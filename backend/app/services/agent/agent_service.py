"""Agent Service — LLM brain with function calling and SSE streaming."""

import json
import logging
from typing import AsyncGenerator, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI
from app.core.config import settings
from app.db import models
from app.services.agent.tools import registry

# Ensure tool handlers are registered
import app.services.agent.tool_handlers  # noqa: F401

logger = logging.getLogger(__name__)

# Tool name → contextual follow-up suggestions
TOOL_SUGGESTIONS: dict[str, list[dict[str, str]]] = {
    "list_datasets": [
        {"label": "预览数据集内容", "prompt": "帮我预览一下刚才列出的数据集内容"},
        {"label": "创建评测任务", "prompt": "帮我用这些数据集创建一个评测任务"},
        {"label": "查看模型列表", "prompt": "查看我的所有模型"},
    ],
    "list_models": [
        {"label": "测试模型连接", "prompt": "帮我测试一下模型的API连接"},
        {"label": "添加新模型", "prompt": "帮我添加一个新模型"},
        {"label": "创建评测任务", "prompt": "帮我创建一个评测任务"},
    ],
    "list_evaluations": [
        {"label": "查看评测详情", "prompt": "查看最近一个评测任务的详情"},
        {"label": "对比分析", "prompt": "帮我对比分析这些评测任务"},
        {"label": "创建新评测", "prompt": "帮我创建一个新的评测任务"},
    ],
    "create_evaluation": [
        {"label": "查看任务进度", "prompt": "查看刚创建的评测任务进度"},
        {"label": "查看任务列表", "prompt": "查看所有评测任务列表"},
    ],
    "get_evaluation_status": [
        {"label": "查看评测结果", "prompt": "查看这个评测的详细结果"},
        {"label": "生成报告", "prompt": "帮我生成这个评测的报告"},
        {"label": "诊断低分样本", "prompt": "帮我诊断这个评测中的低分样本"},
        {"label": "失败案例分析", "prompt": "分析这个评测中的失败案例"},
    ],
    "get_evaluation_results": [
        {"label": "生成报告", "prompt": "帮我生成评测报告"},
        {"label": "失败分析", "prompt": "分析评测中的失败案例"},
        {"label": "诊断低分样本", "prompt": "帮我诊断低分样本并生成优化数据"},
        {"label": "对比分析", "prompt": "对比多个评测结果"},
    ],
    "get_elo_leaderboard": [
        {"label": "发起竞技场对战", "prompt": "帮我在竞技场发起一场模型对战"},
        {"label": "查看基准排行", "prompt": "查看基准测试排行榜"},
    ],
    "get_benchmark_leaderboard": [
        {"label": "发起竞技场", "prompt": "带我去竞技场发起一场对战"},
        {"label": "ELO排行榜", "prompt": "查看ELO排行榜"},
    ],
    "generate_report": [
        {"label": "查看报告列表", "prompt": "查看所有报告列表"},
        {"label": "下载报告", "prompt": "帮我下载这个报告"},
    ],
    "test_model": [
        {"label": "创建评测", "prompt": "用这个模型创建一个评测任务"},
        {"label": "查看模型列表", "prompt": "查看我的所有模型"},
    ],
    "compare_evaluations": [
        {"label": "生成报告", "prompt": "帮我生成对比报告"},
        {"label": "查看排行榜", "prompt": "查看排行榜"},
    ],
    "analyze_failures": [
        {"label": "推荐评测配置", "prompt": "根据失败分析推荐更好的评测配置"},
        {"label": "重新评测", "prompt": "用优化后的配置重新评测"},
    ],
    "suggest_evaluation_config": [
        {"label": "立即创建评测", "prompt": "按照推荐配置立即创建评测"},
        {"label": "预估费用", "prompt": "帮我预估这个配置的评测费用"},
    ],
    "estimate_cost": [
        {"label": "创建评测", "prompt": "按照当前配置创建评测任务"},
        {"label": "调整配置", "prompt": "帮我调整评测配置以降低费用"},
    ],
    "get_overview": [
        {"label": "查看数据集", "prompt": "查看数据集列表"},
        {"label": "查看模型", "prompt": "查看模型列表"},
        {"label": "查看评测任务", "prompt": "查看评测任务列表"},
        {"label": "创建评测", "prompt": "帮我创建一个评测任务"},
    ],
    "navigate_to_page": [
        {"label": "查看概览", "prompt": "查看我的概览数据"},
        {"label": "查看评测", "prompt": "查看评测任务列表"},
    ],
    "preview_dataset": [
        {"label": "创建评测", "prompt": "用这个数据集创建评测任务"},
        {"label": "查看其他数据集", "prompt": "查看数据集列表"},
    ],
    "quick_test_model": [
        {"label": "再测试一个问题", "prompt": "再用另一个问题测试一下这个模型"},
        {"label": "创建评测", "prompt": "帮我创建一个评测任务"},
    ],
    "run_healthbench": [
        {"label": "查看评测进度", "prompt": "查看刚创建的HealthBench评测任务进度"},
        {"label": "查看评测结果", "prompt": "查看HealthBench评测的详细结果"},
        {"label": "对比医疗能力", "prompt": "对比不同模型的医疗健康评测表现"},
    ],
    "run_domain_evaluation": [
        {"label": "查看评测进度", "prompt": "查看领域评测任务的进度"},
        {"label": "查看评测结果", "prompt": "查看领域评测的详细结果"},
    ],
    "diagnose_evaluation": [
        {"label": "生成训练数据", "prompt": "基于诊断结果生成修正版训练数据"},
        {"label": "查看诊断详情", "prompt": "查看评测结果中的诊断详情"},
    ],
    "generate_training_data": [
        {"label": "审核优化数据", "prompt": "带我去审核生成的优化数据"},
        {"label": "导出数据集", "prompt": "将优化数据导出为新数据集"},
    ],
    "export_optimized_dataset": [
        {"label": "查看新数据集", "prompt": "查看数据集列表"},
        {"label": "创建新评测", "prompt": "用导出的数据集创建一个新评测"},
    ],
    "list_prompt_templates": [
        {"label": "创建提示词", "prompt": "帮我创建一个新的提示词模板"},
        {"label": "领域评测", "prompt": "帮我用这些提示词做一次领域评测"},
    ],
    "create_prompt_template": [
        {"label": "查看提示词", "prompt": "查看提示词模板列表"},
        {"label": "创建领域评测", "prompt": "帮我用这个提示词创建一次领域评测"},
    ],
}

DEFAULT_SUGGESTIONS: list[dict[str, str]] = [
    {"label": "查看数据集", "prompt": "查看数据集列表"},
    {"label": "查看模型", "prompt": "查看我的所有模型"},
    {"label": "查看评测", "prompt": "查看评测任务列表"},
    {"label": "平台概览", "prompt": "查看我的概览数据"},
]

SYSTEM_PROMPT = """你是 LLM 评测平台的 AI 助手，拥有 35 个工具可以全面操控平台。你的能力包括：

**模型管理 (6个工具)**
- 查看、创建、更新、删除模型配置
- 测试模型API连接是否可用
- 支持 OpenAI / Anthropic / Azure / 自定义 API

**数据集管理 (4个工具)**
- 查看数据集列表和详情
- 预览数据集内容（前N条）
- 删除数据集

**评测任务 (5个工具)**
- 创建评测任务（支持性能、LLM裁判、幻觉检测、安全性、鲁棒性、一致性、代码执行、RAG、多轮对话、指令跟随、推理链、长上下文、结构化输出、多语言、工具调用、多模态、成本分析等维度）
- 查看任务列表和详情、取消任务、重试失败任务
- 获取逐条评测结果

**报告生成 (3个工具)**
- 生成 PDF/Excel/JSON 格式报告
- 查看报告列表和下载链接

**排行榜 (2个工具)**
- 查看 ELO 排行榜
- 查看基准测试排行

**基准测试 (1个工具)**
- 查看17种标准基准测试（含 HealthBench 医疗评测三个变体）

**HealthBench 医疗评测 (1个工具)**
- 快速运行 HealthBench 医疗健康评测基准（OpenAI发布，262位医生标注，7大主题5个维度）
- 支持完整版、困难版、共识版三个变体

**页面导航 (1个工具)**
- 跳转到任意平台页面和详情页

**系统管理 (4个工具)**
- 查看平台/个人统计数据
- 列出和管理用户（管理员）
- 查询审计日志

**提示词工程 (2个工具)**
- 查看和创建提示词模板（支持 generation 生成提示词和 evaluation 评测提示词两种类型）
- 支持按领域筛选（医疗、金融、工业、法律、教育、通用）

**垂直领域评测 (4个工具)**
- 创建垂直领域评测（双Prompt模式：生成提示词给被测模型 + 评测提示词给上位评判模型）
- 诊断低分样本（自动分析扣分原因和问题片段）
- 生成修正版训练数据（上位模型自动纠正低质量回答）
- 导出优化数据集（用于模型再微调的JSONL数据集）

**智能分析 (6个工具)**
- 多任务对比分析：对比不同评测任务的得分
- 失败案例分析：聚类错误类型，发现模型薄弱环节
- 智能配置推荐：根据模型和目标推荐评测配置
- 费用预估：预测评测的token消耗和费用
- 分数解读：解释评测指标含义并给出改进建议
- 记忆保存：记住用户偏好以提供个性化服务

**高级技能 (3个工具)**
- 快速测试模型（发送问题直接获取回复）
- 获取个人综合概览（模型、数据集、评测状态分布）
- 运行 HealthBench 医疗评测（一键启动医疗能力评测）

**完整闭环示例**：
用户说"帮我做一次医疗领域评测" →
1. 查看用户模型列表 → 确认被测模型
2. 查看医疗领域提示词 → 确认生成和评测提示词
3. 创建垂直领域评测 → 任务开始运行
4. 评测完成后，建议用户"诊断低分样本"
5. 诊断完成后，建议"生成修正版训练数据"
6. 生成后，引导用户去优化页面审核数据
7. 用户审核后，帮助导出新数据集 → 闭环完成

**交互原则**：
- 请用中文与用户交流，回答简洁专业
- 当需要具体参数但用户没有提供时，主动询问
- 对于复杂操作（如创建评测），分步引导用户确认参数
- 当发现用户的使用偏好时（如常用模型、评测配置等），可以使用save_memory工具记住
- 在完成一个操作后，主动建议下一步操作（如评测完成后建议查看结果或诊断）
- 如果用户的评测包含垂直领域配置，完成后主动提醒可以进行"诊断→优化→导出"的闭环流程

**格式要求（必须严格遵守）**：
- 当展示列表（数据集、模型、评测任务等）时，必须使用工具返回数据中的"序号"字段作为编号，以有序列表格式展示。每一项的格式必须是 `数字. 空格 内容`（如 `1. 第一项`），数字后面必须紧跟英文句点和一个空格，然后才是内容文字。确保编号从1开始连续递增。
- 禁止所有列表项都使用相同编号或无编号的格式。
- 禁止使用 `1.内容` 这种数字和内容之间没有空格的格式，必须写成 `1. 内容`。"""


class AgentService:
    def __init__(self, db: AsyncSession, user: models.User, agent_config: dict = None):
        self.db = db
        self.user = user
        import httpx
        # Use AsyncHTTPTransport to bypass ALL_PROXY socks5 (not supported by httpx)
        http_client = httpx.AsyncClient(
            transport=httpx.AsyncHTTPTransport(),
            timeout=httpx.Timeout(120.0, connect=30.0),
        )

        # Use DB config if provided, otherwise fall back to env/settings defaults
        if agent_config:
            api_key = agent_config.get("api_key") or settings.AGENT_API_KEY or "sk-placeholder"
            base_url = agent_config.get("base_url") or settings.AGENT_BASE_URL
            self._model_name = agent_config.get("model_name") or settings.AGENT_MODEL_NAME
            self._max_tokens = agent_config.get("max_tokens") or settings.AGENT_MAX_TOKENS
            self._temperature = agent_config.get("temperature") if agent_config.get("temperature") is not None else settings.AGENT_TEMPERATURE
            extra_params = agent_config.get("params") or {}
            self._top_p = extra_params.get("top_p")
            self._top_k = extra_params.get("top_k")
            self._repetition_penalty = extra_params.get("repetition_penalty")
            self._presence_penalty = extra_params.get("presence_penalty")
        else:
            api_key = settings.AGENT_API_KEY or "sk-placeholder"
            base_url = settings.AGENT_BASE_URL
            self._model_name = settings.AGENT_MODEL_NAME
            self._max_tokens = settings.AGENT_MAX_TOKENS
            self._temperature = settings.AGENT_TEMPERATURE
            self._top_p = None
            self._top_k = None
            self._repetition_penalty = None
            self._presence_penalty = None

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=http_client,
        )

    async def _get_or_create_conversation(
        self, conversation_id: Optional[int] = None
    ) -> models.AgentConversation:
        if conversation_id:
            result = await self.db.execute(
                select(models.AgentConversation).where(
                    models.AgentConversation.id == conversation_id,
                    models.AgentConversation.user_id == self.user.id,
                )
            )
            conv = result.scalar_one_or_none()
            if conv:
                return conv

        conv = models.AgentConversation(user_id=self.user.id)
        self.db.add(conv)
        await self.db.flush()
        await self.db.refresh(conv)
        return conv

    async def _load_history(self, conversation: models.AgentConversation) -> list[dict]:
        result = await self.db.execute(
            select(models.AgentMessage)
            .where(models.AgentMessage.conversation_id == conversation.id)
            .order_by(models.AgentMessage.created_at)
        )
        rows = result.scalars().all()
        messages = []
        for msg in rows:
            m = {"role": msg.role}
            if msg.content:
                m["content"] = msg.content
            if msg.tool_calls:
                m["tool_calls"] = msg.tool_calls
            if msg.role == "tool":
                m["tool_call_id"] = msg.tool_call_id
                m["content"] = msg.content or ""
            messages.append(m)
        return messages

    async def _save_message(
        self,
        conversation: models.AgentConversation,
        role: str,
        content: Optional[str] = None,
        tool_calls: Optional[list] = None,
        tool_call_id: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> models.AgentMessage:
        msg = models.AgentMessage(
            conversation_id=conversation.id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
        )
        self.db.add(msg)
        await self.db.flush()
        return msg

    async def _execute_tool(self, name: str, arguments: dict) -> dict:
        tool_def = registry.get_tool(name)
        if not tool_def:
            return {"error": f"Unknown tool: {name}"}

        try:
            import inspect
            sig = inspect.signature(tool_def.handler)
            call_kwargs = {}
            if "db" in sig.parameters:
                call_kwargs["db"] = self.db
            if "user" in sig.parameters:
                call_kwargs["user"] = self.user
            call_kwargs.update(arguments)
            result = await registry.execute(name, **call_kwargs)
            return result
        except Exception as e:
            logger.exception(f"Tool execution error: {name}")
            return {"error": str(e)}

    async def _load_memories(self) -> str:
        """Load user memories to inject into system prompt."""
        result = await self.db.execute(
            select(models.AgentMemory)
            .where(models.AgentMemory.user_id == self.user.id)
            .order_by(models.AgentMemory.access_count.desc())
            .limit(20)
        )
        memories = result.scalars().all()
        if not memories:
            return ""

        lines = ["\n\n**用户记忆（请参考以下信息个性化回复）:**"]
        for m in memories:
            lines.append(f"- [{m.memory_type}] {m.key}: {m.value}")
            m.access_count += 1
        await self.db.flush()
        return "\n".join(lines)

    def _build_context_prompt(self, context: Optional[dict]) -> str:
        """Build context-aware prompt section from frontend context."""
        if not context:
            return ""

        parts = ["\n\n**当前页面上下文:**"]
        route = context.get("current_route", "")
        if route:
            route_descriptions = {
                "/dashboard": "用户正在查看仪表盘概览页面",
                "/models": "用户正在查看模型管理页面",
                "/datasets": "用户正在查看数据集管理页面",
                "/evaluations": "用户正在查看评测任务列表",
                "/evaluations/new": "用户正在创建新的评测任务",
                "/leaderboard": "用户正在查看ELO排行榜",
                "/benchmarks": "用户正在查看标准基准测试",
                "/comparison": "用户正在查看评测对比分析",
                "/prompts": "用户正在查看提示词工程页面",
                "/arena": "用户正在模型竞技场",
                "/teams": "用户正在查看团队协作页面",
                "/settings/api-keys": "用户正在管理API密钥",
                "/admin": "用户正在系统管理页面",
            }
            # Handle dynamic routes
            desc = route_descriptions.get(route)
            if not desc:
                if "/evaluations/" in route and "/optimize" in route:
                    desc = "用户正在查看评测优化页面（诊断低分样本→生成修正数据→导出新数据集）。可以帮助用户审核数据、导出数据集或解释优化流程。"
                elif "/results/" in route:
                    desc = "用户正在查看评测结果详情页面（图表、分数分布、逐条结果）。可以帮助分析结果、诊断低分样本或生成报告。"
                elif "/evaluations/" in route:
                    desc = "用户正在查看某个评测任务的详情和进度。可以帮助查看结果、诊断或优化。"
                else:
                    desc = f"用户当前在 {route} 页面"
            parts.append(f"- 当前路由: {route} ({desc})")

        page_data = context.get("current_page_data")
        if page_data:
            parts.append(f"- 页面数据: {json.dumps(page_data, ensure_ascii=False)[:500]}")

        parts.append("请根据用户当前所在页面，优先提供与当前页面相关的帮助和建议。")
        return "\n".join(parts)

    async def chat_stream(
        self, message: str, conversation_id: Optional[int] = None,
        context: Optional[dict] = None,
    ) -> AsyncGenerator[str, None]:
        conversation = await self._get_or_create_conversation(conversation_id)

        # Emit conversation id
        yield f"event: message_start\ndata: {json.dumps({'conversation_id': conversation.id})}\n\n"

        # Update title from first message
        if not conversation_id:
            conversation.title = message[:50] + ("..." if len(message) > 50 else "")
            await self.db.flush()

        # Save user message
        await self._save_message(conversation, "user", content=message)

        # Build system prompt with context and memories
        memory_section = await self._load_memories()
        context_section = self._build_context_prompt(context)
        system_content = SYSTEM_PROMPT + context_section + memory_section

        # Load history
        history = await self._load_history(conversation)
        api_messages = [{"role": "system", "content": system_content}] + history

        tools = registry.to_openai_tools()
        tool_round = 0
        called_tool_names: list[str] = []

        while tool_round < settings.AGENT_MAX_TOOL_CALLS_PER_TURN:  # max tool rounds still from settings
            try:
                extra_body: dict = {
                    "chat_template_kwargs": {"enable_thinking": False},
                }
                if self._top_k is not None:
                    extra_body["top_k"] = self._top_k
                if self._repetition_penalty is not None:
                    extra_body["repetition_penalty"] = self._repetition_penalty

                create_kwargs: dict = {
                    "model": self._model_name,
                    "messages": api_messages,
                    "tools": tools if tools else None,
                    "temperature": self._temperature,
                    "max_tokens": self._max_tokens,
                    "stream": True,
                    "extra_body": extra_body,
                }
                if self._top_p is not None:
                    create_kwargs["top_p"] = self._top_p
                if self._presence_penalty is not None:
                    create_kwargs["presence_penalty"] = self._presence_penalty

                stream = await self.client.chat.completions.create(**create_kwargs)
            except Exception as e:
                logger.exception("LLM API call failed")
                yield f"event: error\ndata: {json.dumps({'error': f'LLM API 调用失败: {str(e)}'})}\n\n"
                return

            # Accumulate streamed response
            full_content = ""
            tool_calls_acc: dict[int, dict] = {}

            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if not delta:
                    continue

                # Stream text content
                if delta.content:
                    full_content += delta.content
                    yield f"event: content_delta\ndata: {json.dumps({'content': delta.content})}\n\n"

                # Accumulate tool calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {
                                "id": tc.id or "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }
                        if tc.id:
                            tool_calls_acc[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls_acc[idx]["function"]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_calls_acc[idx]["function"]["arguments"] += tc.function.arguments

            # Process accumulated tool calls
            if tool_calls_acc:
                tool_calls_list = [tool_calls_acc[i] for i in sorted(tool_calls_acc.keys())]

                # Save assistant message with tool calls
                await self._save_message(
                    conversation, "assistant",
                    content=full_content if full_content else None,
                    tool_calls=tool_calls_list,
                )

                # Add assistant message to API messages once (before tool results)
                api_messages.append({
                    "role": "assistant",
                    "content": full_content if full_content else None,
                    "tool_calls": tool_calls_list,
                })

                # Execute each tool
                for tc in tool_calls_list:
                    fn_name = tc["function"]["name"]
                    try:
                        fn_args = json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
                    except json.JSONDecodeError:
                        fn_args = {}

                    yield f"event: tool_call_start\ndata: {json.dumps({'tool_call_id': tc['id'], 'name': fn_name, 'arguments': fn_args})}\n\n"

                    called_tool_names.append(fn_name)
                    result = await self._execute_tool(fn_name, fn_args)
                    result_str = json.dumps(result, ensure_ascii=False, default=str)

                    # Check for navigation
                    if isinstance(result, dict) and "navigate" in result:
                        yield f"event: navigate\ndata: {json.dumps({'path': result['navigate']})}\n\n"

                    yield f"event: tool_result\ndata: {json.dumps({'tool_call_id': tc['id'], 'name': fn_name, 'result': result})}\n\n"

                    # Save tool result message
                    await self._save_message(
                        conversation, "tool",
                        content=result_str,
                        tool_call_id=tc["id"],
                        tool_name=fn_name,
                    )

                    # Add tool result to API messages for next LLM round
                    api_messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result_str,
                    })

                tool_round += 1
                # Continue loop to let LLM process tool results
                continue

            # No tool calls — save final assistant message and finish
            if full_content:
                await self._save_message(conversation, "assistant", content=full_content)

            break

        # Emit contextual suggestions based on the last called tool
        suggestions = DEFAULT_SUGGESTIONS
        if called_tool_names:
            last_tool = called_tool_names[-1]
            suggestions = TOOL_SUGGESTIONS.get(last_tool, DEFAULT_SUGGESTIONS)
        yield f"event: suggestions\ndata: {json.dumps({'suggestions': suggestions}, ensure_ascii=False)}\n\n"

        yield f"event: message_end\ndata: {json.dumps({'conversation_id': conversation.id})}\n\n"
