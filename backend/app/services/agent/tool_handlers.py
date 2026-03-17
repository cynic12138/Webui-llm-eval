"""
Agent Tool Handlers — comprehensive Skills-Agent-Tools coverage.
Each tool operates directly on DB models / existing services.

Categories:
  - models      (8 tools): CRUD + test connectivity + judge models (list, create)
  - datasets    (4 tools): list, preview, get, delete
  - evaluations (8 tools): create, list, status, cancel, results, retry, delete, batch delete
  - reports     (3 tools): generate, list, download url
  - leaderboard (2 tools): ELO rankings, benchmark aggregation
  - benchmarks  (1 tool):  list available benchmarks
  - navigation  (1 tool):  frontend route navigation
  - admin       (3 tools): stats, list users, toggle user
  - prompts     (5 tools): list, create, get, update, delete templates + run experiment
  - analysis    (6 tools): compare, failures, suggest, cost, explain, memory
  - skills      (2 tools): full pipeline, quick model test
  - domain_eval (4 tools): run domain eval, diagnose, generate data, export
"""

import json
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import models
from app.core.security import encrypt_api_key
from app.services.agent.tools import registry


# ────────────────────────── Models ──────────────────────────

@registry.register(
    name="list_models",
    description="列出当前用户的所有模型配置，包括名称、服务商、模型名、状态等",
    category="models",
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
)
async def list_models(db: AsyncSession, user: models.User, **kwargs):
    result = await db.execute(
        select(models.ModelConfig).where(models.ModelConfig.user_id == user.id)
    )
    rows = result.scalars().all()
    return {
        "total": len(rows),
        "models": [
            {
                "序号": i + 1,
                "id": m.id, "name": m.name, "provider": m.provider,
                "model_name": m.model_name, "base_url": m.base_url,
                "is_active": m.is_active, "created_at": m.created_at.isoformat(),
            }
            for i, m in enumerate(rows)
        ],
    }


@registry.register(
    name="get_model",
    description="获取指定模型配置的详细信息",
    category="models",
    parameters={
        "type": "object",
        "properties": {
            "model_id": {"type": "integer", "description": "模型配置ID"},
        },
        "required": ["model_id"],
    },
)
async def get_model(db: AsyncSession, user: models.User, **kwargs):
    result = await db.execute(
        select(models.ModelConfig).where(
            models.ModelConfig.id == kwargs["model_id"],
            models.ModelConfig.user_id == user.id,
        )
    )
    m = result.scalar_one_or_none()
    if not m:
        return {"error": "模型不存在或无权限"}
    return {
        "id": m.id, "name": m.name, "provider": m.provider,
        "model_name": m.model_name, "base_url": m.base_url,
        "is_active": m.is_active, "params": m.params or {},
        "created_at": m.created_at.isoformat(),
    }


@registry.register(
    name="create_model",
    description="创建一个新的模型配置。需要提供名称、服务商(openai/anthropic/custom)、模型名、可选API密钥和base_url",
    category="models",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "模型配置名称，如 'GPT-4o 生产环境'"},
            "provider": {"type": "string", "enum": ["openai", "anthropic", "azure", "custom"], "description": "服务商"},
            "model_name": {"type": "string", "description": "模型名称, 如 gpt-4o, claude-3-opus"},
            "api_key": {"type": "string", "description": "API密钥(可选，将加密存储)"},
            "base_url": {"type": "string", "description": "自定义API地址(可选)，如 https://api.openai.com/v1"},
        },
        "required": ["name", "provider", "model_name"],
    },
)
async def create_model(db: AsyncSession, user: models.User, **kwargs):
    encrypted_key = None
    if kwargs.get("api_key"):
        encrypted_key = encrypt_api_key(kwargs["api_key"])

    model = models.ModelConfig(
        user_id=user.id,
        name=kwargs["name"],
        provider=kwargs["provider"],
        api_key_encrypted=encrypted_key,
        base_url=kwargs.get("base_url"),
        model_name=kwargs["model_name"],
        params={},
    )
    db.add(model)
    await db.flush()

    elo = models.ModelEloScore(model_config_id=model.id, model_name=kwargs["name"])
    db.add(elo)
    await db.flush()
    await db.refresh(model)
    return {
        "id": model.id, "name": model.name, "provider": model.provider,
        "model_name": model.model_name,
        "message": f"模型 '{model.name}' 创建成功 (ID: {model.id})",
    }


@registry.register(
    name="update_model",
    description="更新模型配置，可修改名称、API密钥、base_url、模型名、参数、启用/禁用状态",
    category="models",
    parameters={
        "type": "object",
        "properties": {
            "model_id": {"type": "integer", "description": "要更新的模型ID"},
            "name": {"type": "string", "description": "新名称(可选)"},
            "api_key": {"type": "string", "description": "新API密钥(可选)"},
            "base_url": {"type": "string", "description": "新API地址(可选)"},
            "model_name": {"type": "string", "description": "新模型名(可选)"},
            "is_active": {"type": "boolean", "description": "启用/禁用(可选)"},
        },
        "required": ["model_id"],
    },
)
async def update_model(db: AsyncSession, user: models.User, **kwargs):
    result = await db.execute(
        select(models.ModelConfig).where(
            models.ModelConfig.id == kwargs["model_id"],
            models.ModelConfig.user_id == user.id,
        )
    )
    model = result.scalar_one_or_none()
    if not model:
        return {"error": "模型不存在或无权限"}

    updates = []
    if "name" in kwargs and kwargs["name"] is not None:
        model.name = kwargs["name"]
        updates.append("名称")
    if "api_key" in kwargs and kwargs["api_key"] is not None:
        model.api_key_encrypted = encrypt_api_key(kwargs["api_key"])
        updates.append("API密钥")
    if "base_url" in kwargs and kwargs["base_url"] is not None:
        model.base_url = kwargs["base_url"]
        updates.append("API地址")
    if "model_name" in kwargs and kwargs["model_name"] is not None:
        model.model_name = kwargs["model_name"]
        updates.append("模型名")
    if "is_active" in kwargs and kwargs["is_active"] is not None:
        model.is_active = kwargs["is_active"]
        updates.append("状态")

    await db.flush()
    await db.refresh(model)
    return {
        "id": model.id, "name": model.name,
        "message": f"模型 '{model.name}' 已更新: {', '.join(updates)}" if updates else "无变更",
    }


@registry.register(
    name="delete_model",
    description="删除指定ID的模型配置（不可恢复）",
    category="models",
    parameters={
        "type": "object",
        "properties": {
            "model_id": {"type": "integer", "description": "要删除的模型ID"},
        },
        "required": ["model_id"],
    },
    requires_confirmation=True,
)
async def delete_model(db: AsyncSession, user: models.User, **kwargs):
    result = await db.execute(
        select(models.ModelConfig).where(
            models.ModelConfig.id == kwargs["model_id"],
            models.ModelConfig.user_id == user.id,
        )
    )
    model = result.scalar_one_or_none()
    if not model:
        return {"error": "模型不存在或无权限"}
    name = model.name
    await db.delete(model)
    await db.flush()
    return {"message": f"模型 '{name}' (ID: {kwargs['model_id']}) 已删除"}


@registry.register(
    name="test_model_connection",
    description="测试模型API连接是否可用，发送一个简单的请求验证API密钥和地址是否正确",
    category="models",
    parameters={
        "type": "object",
        "properties": {
            "model_id": {"type": "integer", "description": "模型配置ID"},
        },
        "required": ["model_id"],
    },
)
async def test_model_connection(db: AsyncSession, user: models.User, **kwargs):
    from app.core.security import decrypt_api_key
    from app.core.http import make_async_httpx_client
    import time

    result = await db.execute(
        select(models.ModelConfig).where(
            models.ModelConfig.id == kwargs["model_id"],
            models.ModelConfig.user_id == user.id,
        )
    )
    model = result.scalar_one_or_none()
    if not model:
        return {"error": "模型不存在或无权限"}

    api_key = decrypt_api_key(model.api_key_encrypted) if model.api_key_encrypted else None
    if not api_key:
        return {"error": "模型未配置API密钥，无法测试"}

    base_url = model.base_url or "https://api.openai.com/v1"
    url = f"{base_url}/chat/completions"

    try:
        start = time.time()
        async with make_async_httpx_client(timeout=30.0) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model.model_name,
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                },
            )
        latency = round((time.time() - start) * 1000)

        if resp.status_code == 200:
            return {
                "status": "success",
                "latency_ms": latency,
                "message": f"模型 '{model.name}' 连接成功 (延迟 {latency}ms)",
            }
        else:
            return {
                "status": "failed",
                "http_status": resp.status_code,
                "detail": resp.text[:200],
                "message": f"连接失败: HTTP {resp.status_code}",
            }
    except Exception as e:
        return {"status": "error", "message": f"连接错误: {str(e)}"}


# ────────────────────────── Datasets ──────────────────────────

@registry.register(
    name="list_datasets",
    description="列出当前用户的所有数据集，包括名称、分类、格式、大小、状态",
    category="datasets",
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
)
async def list_datasets(db: AsyncSession, user: models.User, **kwargs):
    result = await db.execute(
        select(models.Dataset).where(models.Dataset.user_id == user.id)
    )
    rows = result.scalars().all()
    return {
        "total": len(rows),
        "datasets": [
            {
                "序号": i + 1,
                "id": d.id, "name": d.name, "category": d.category,
                "format": d.format, "size": d.size, "status": d.status,
                "description": d.description, "created_at": d.created_at.isoformat(),
            }
            for i, d in enumerate(rows)
        ],
    }


@registry.register(
    name="get_dataset",
    description="获取指定数据集的详细信息，包括字段结构和样例",
    category="datasets",
    parameters={
        "type": "object",
        "properties": {
            "dataset_id": {"type": "integer", "description": "数据集ID"},
        },
        "required": ["dataset_id"],
    },
)
async def get_dataset(db: AsyncSession, user: models.User, **kwargs):
    result = await db.execute(
        select(models.Dataset).where(
            models.Dataset.id == kwargs["dataset_id"],
            models.Dataset.user_id == user.id,
        )
    )
    d = result.scalar_one_or_none()
    if not d:
        return {"error": "数据集不存在或无权限"}
    return {
        "id": d.id, "name": d.name, "category": d.category,
        "format": d.format, "size": d.size, "status": d.status,
        "description": d.description, "schema_meta": d.schema_meta,
        "created_at": d.created_at.isoformat(),
    }


@registry.register(
    name="preview_dataset",
    description="预览数据集的前N条记录内容",
    category="datasets",
    parameters={
        "type": "object",
        "properties": {
            "dataset_id": {"type": "integer", "description": "数据集ID"},
            "limit": {"type": "integer", "description": "预览条数(默认5)", "default": 5},
        },
        "required": ["dataset_id"],
    },
)
async def preview_dataset(db: AsyncSession, user: models.User, **kwargs):
    result = await db.execute(
        select(models.Dataset).where(
            models.Dataset.id == kwargs["dataset_id"],
            models.Dataset.user_id == user.id,
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        return {"error": "数据集不存在或无权限"}

    from app.services.storage import StorageService
    storage = StorageService()
    content = await storage.download_bytes(dataset.file_path)
    records = []
    limit = kwargs.get("limit", 5)
    if dataset.format == "jsonl":
        for i, line in enumerate(content.decode("utf-8").strip().split("\n")):
            if i >= limit:
                break
            if line.strip():
                records.append(json.loads(line))
    return {"dataset": dataset.name, "total": dataset.size, "preview": records}


@registry.register(
    name="delete_dataset",
    description="删除指定的数据集（包括存储文件，不可恢复）",
    category="datasets",
    parameters={
        "type": "object",
        "properties": {
            "dataset_id": {"type": "integer", "description": "要删除的数据集ID"},
        },
        "required": ["dataset_id"],
    },
    requires_confirmation=True,
)
async def delete_dataset(db: AsyncSession, user: models.User, **kwargs):
    result = await db.execute(
        select(models.Dataset).where(
            models.Dataset.id == kwargs["dataset_id"],
            models.Dataset.user_id == user.id,
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        return {"error": "数据集不存在或无权限"}

    name = dataset.name
    # Delete file from storage
    if dataset.file_path:
        try:
            from app.services.storage import StorageService
            storage = StorageService()
            await storage.delete_file(dataset.file_path)
        except Exception:
            pass  # File might already be gone

    await db.delete(dataset)
    await db.flush()
    return {"message": f"数据集 '{name}' (ID: {kwargs['dataset_id']}) 已删除"}


# ────────────────────────── Evaluations ──────────────────────────

@registry.register(
    name="create_evaluation",
    description="创建并启动一个新的评测任务。需要任务名、模型ID列表；可选数据集ID、基准测试列表和各种评测维度开关",
    category="evaluations",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "评测任务名称"},
            "model_ids": {"type": "array", "items": {"type": "integer"}, "description": "参与评测的模型ID列表"},
            "dataset_id": {"type": "integer", "description": "数据集ID(可选)"},
            "description": {"type": "string", "description": "任务描述(可选)"},
            "benchmarks": {"type": "array", "items": {"type": "string", "enum": ["mmlu_pro", "gsm8k", "humaneval", "ceval", "hellaswag", "truthfulqa", "math", "arc", "mt_bench", "alpaca_eval", "ifeval", "swe_bench", "bigcodebench", "livebench", "healthbench", "healthbench_hard", "healthbench_consensus"]}, "description": "基准测试（含HealthBench医疗评测）"},
            "performance": {"type": "boolean", "description": "是否评测性能指标(默认true)"},
            "llm_judge": {"type": "boolean", "description": "是否启用LLM裁判评分"},
            "judge_model_id": {"type": "integer", "description": "裁判模型的ID(启用llm_judge时需要)"},
            "hallucination": {"type": "boolean", "description": "是否检测幻觉"},
            "safety": {"type": "boolean", "description": "是否检测安全性/毒性"},
            "robustness": {"type": "boolean", "description": "是否测试鲁棒性"},
            "consistency": {"type": "boolean", "description": "是否测试一致性"},
            "code_execution": {"type": "boolean", "description": "是否执行代码验证"},
            "rag_eval": {"type": "boolean", "description": "是否进行RAG评测"},
            "multiturn": {"type": "boolean", "description": "是否进行多轮对话评测"},
            "instruction_following": {"type": "boolean", "description": "是否进行指令遵循评测(IFEval)"},
            "cot_reasoning": {"type": "boolean", "description": "是否进行思维链推理评测"},
            "long_context": {"type": "boolean", "description": "是否进行长上下文评测(Needle-in-a-Haystack)"},
            "structured_output": {"type": "boolean", "description": "是否进行结构化输出评测(JSON Schema验证)"},
            "multilingual": {"type": "boolean", "description": "是否进行多语言评测"},
            "tool_calling": {"type": "boolean", "description": "是否进行工具调用评测"},
            "multimodal": {"type": "boolean", "description": "是否进行多模态(图文)评测"},
            "cost_analysis": {"type": "boolean", "description": "是否进行性价比分析"},
            "max_samples": {"type": "integer", "description": "最大评测样本数"},
        },
        "required": ["name", "model_ids"],
    },
)
async def create_evaluation(db: AsyncSession, user: models.User, **kwargs):
    for mid in kwargs["model_ids"]:
        result = await db.execute(
            select(models.ModelConfig).where(
                models.ModelConfig.id == mid,
                models.ModelConfig.user_id == user.id,
            )
        )
        if not result.scalar_one_or_none():
            return {"error": f"模型 ID {mid} 不存在或无权限"}

    evaluator_config = {"performance": kwargs.get("performance", True)}
    for key in ["benchmarks", "llm_judge", "judge_model_id", "hallucination",
                 "safety", "robustness", "consistency", "code_execution",
                 "rag_eval", "multiturn", "instruction_following", "cot_reasoning",
                 "long_context", "structured_output", "multilingual",
                 "tool_calling", "multimodal", "cost_analysis", "max_samples"]:
        if key in kwargs and kwargs[key] is not None:
            evaluator_config[key] = kwargs[key]

    task = models.EvaluationTask(
        user_id=user.id,
        name=kwargs["name"],
        description=kwargs.get("description"),
        model_ids=kwargs["model_ids"],
        dataset_id=kwargs.get("dataset_id"),
        evaluator_config=evaluator_config,
        status="pending",
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)

    # Commit BEFORE dispatching Celery to avoid race condition
    await db.commit()

    from app.services.evaluation import run_evaluation_task
    celery_result = run_evaluation_task.delay(task.id)
    task.celery_task_id = celery_result.id
    await db.flush()

    return {
        "id": task.id, "name": task.name, "status": task.status,
        "message": f"评测任务 '{task.name}' 已创建并开始运行 (ID: {task.id})",
        "navigate": f"/evaluations/{task.id}",
    }


@registry.register(
    name="list_evaluations",
    description="列出用户的评测任务，可按状态过滤（pending/running/completed/failed/cancelled）",
    category="evaluations",
    parameters={
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["pending", "running", "completed", "failed", "cancelled"],
                       "description": "按状态过滤(可选)"},
        },
        "required": [],
    },
)
async def list_evaluations(db: AsyncSession, user: models.User, **kwargs):
    query = select(models.EvaluationTask).where(
        models.EvaluationTask.user_id == user.id
    ).order_by(models.EvaluationTask.created_at.desc())

    if kwargs.get("status"):
        query = query.where(models.EvaluationTask.status == kwargs["status"])

    result = await db.execute(query)
    rows = result.scalars().all()
    return {
        "total": len(rows),
        "evaluations": [
            {
                "序号": i + 1,
                "id": t.id, "name": t.name, "status": t.status,
                "progress": t.progress, "model_ids": t.model_ids,
                "total_samples": t.total_samples,
                "processed_samples": t.processed_samples,
                "created_at": t.created_at.isoformat(),
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            }
            for i, t in enumerate(rows)
        ],
    }


@registry.register(
    name="get_evaluation_status",
    description="获取指定评测任务的详情、进度、结果摘要和错误信息",
    category="evaluations",
    parameters={
        "type": "object",
        "properties": {
            "task_id": {"type": "integer", "description": "评测任务ID"},
        },
        "required": ["task_id"],
    },
)
async def get_evaluation_status(db: AsyncSession, user: models.User, **kwargs):
    result = await db.execute(
        select(models.EvaluationTask).where(
            models.EvaluationTask.id == kwargs["task_id"],
            models.EvaluationTask.user_id == user.id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        return {"error": "评测任务不存在或无权限"}
    return {
        "id": task.id, "name": task.name, "status": task.status,
        "progress": task.progress, "total_samples": task.total_samples,
        "processed_samples": task.processed_samples,
        "model_ids": task.model_ids,
        "evaluator_config": task.evaluator_config,
        "results_summary": task.results_summary,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat(),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


@registry.register(
    name="cancel_evaluation",
    description="取消正在运行或等待中的评测任务",
    category="evaluations",
    parameters={
        "type": "object",
        "properties": {
            "task_id": {"type": "integer", "description": "要取消的评测任务ID"},
        },
        "required": ["task_id"],
    },
    requires_confirmation=True,
)
async def cancel_evaluation(db: AsyncSession, user: models.User, **kwargs):
    result = await db.execute(
        select(models.EvaluationTask).where(
            models.EvaluationTask.id == kwargs["task_id"],
            models.EvaluationTask.user_id == user.id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        return {"error": "评测任务不存在或无权限"}
    if task.status in ("completed", "cancelled"):
        return {"error": f"任务已经是 {task.status} 状态，无法取消"}

    if task.celery_task_id:
        from app.core.celery_app import celery_app
        celery_app.control.revoke(task.celery_task_id, terminate=True)

    task.status = "cancelled"
    await db.flush()
    return {"message": f"评测任务 '{task.name}' (ID: {task.id}) 已取消"}


@registry.register(
    name="get_evaluation_results",
    description="获取评测任务中各样本的详细评测结果，包括输入、输出、参考答案、分数、延迟等",
    category="evaluations",
    parameters={
        "type": "object",
        "properties": {
            "task_id": {"type": "integer", "description": "评测任务ID"},
            "model_id": {"type": "integer", "description": "按模型ID过滤(可选)"},
            "limit": {"type": "integer", "description": "返回条数(默认10)", "default": 10},
        },
        "required": ["task_id"],
    },
)
async def get_evaluation_results(db: AsyncSession, user: models.User, **kwargs):
    # Verify ownership
    task_result = await db.execute(
        select(models.EvaluationTask).where(
            models.EvaluationTask.id == kwargs["task_id"],
            models.EvaluationTask.user_id == user.id,
        )
    )
    if not task_result.scalar_one_or_none():
        return {"error": "评测任务不存在或无权限"}

    query = select(models.EvaluationResult).where(
        models.EvaluationResult.task_id == kwargs["task_id"]
    )
    if kwargs.get("model_id"):
        query = query.where(models.EvaluationResult.model_id == kwargs["model_id"])
    query = query.limit(kwargs.get("limit", 10))

    result = await db.execute(query)
    rows = result.scalars().all()
    return {
        "total": len(rows),
        "results": [
            {
                "sample_index": r.sample_index,
                "model_id": r.model_id,
                "input": (r.input_text or "")[:200],
                "output": (r.output_text or "")[:200],
                "reference": (r.reference_text or "")[:200],
                "scores": r.scores,
                "latency_ms": r.latency_ms,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
            }
            for r in rows
        ],
    }


# ────────────────────────── Reports ──────────────────────────

@registry.register(
    name="generate_report",
    description="为已完成的评测任务生成报告，支持 pdf/excel/json 三种格式",
    category="reports",
    parameters={
        "type": "object",
        "properties": {
            "task_id": {"type": "integer", "description": "已完成的评测任务ID"},
            "format": {"type": "string", "enum": ["pdf", "excel", "json"],
                       "description": "报告格式(默认pdf)", "default": "pdf"},
        },
        "required": ["task_id"],
    },
)
async def generate_report(db: AsyncSession, user: models.User, **kwargs):
    task_result = await db.execute(
        select(models.EvaluationTask).where(
            models.EvaluationTask.id == kwargs["task_id"],
            models.EvaluationTask.user_id == user.id,
        )
    )
    task = task_result.scalar_one_or_none()
    if not task:
        return {"error": "评测任务不存在或无权限"}
    if task.status != "completed":
        return {"error": f"评测任务尚未完成 (当前状态: {task.status})"}

    fmt = kwargs.get("format", "pdf")
    from app.services.report import ReportService
    service = ReportService(db)
    report = await service.generate(task, user, fmt)
    return {
        "id": report.id, "format": report.format,
        "file_size": report.file_size,
        "message": f"报告已生成 ({fmt} 格式, ID: {report.id})",
        "download_url": f"/api/v1/reports/{report.id}/download",
    }


@registry.register(
    name="list_reports",
    description="列出用户生成的所有评测报告",
    category="reports",
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
)
async def list_reports(db: AsyncSession, user: models.User, **kwargs):
    result = await db.execute(
        select(models.Report).where(models.Report.user_id == user.id)
        .order_by(models.Report.generated_at.desc())
    )
    rows = result.scalars().all()
    return {
        "total": len(rows),
        "reports": [
            {
                "id": r.id, "task_id": r.task_id, "format": r.format,
                "file_size": r.file_size,
                "generated_at": r.generated_at.isoformat(),
                "download_url": f"/api/v1/reports/{r.id}/download",
            }
            for r in rows
        ],
    }


@registry.register(
    name="get_report_download_url",
    description="获取指定报告的下载链接",
    category="reports",
    parameters={
        "type": "object",
        "properties": {
            "report_id": {"type": "integer", "description": "报告ID"},
        },
        "required": ["report_id"],
    },
)
async def get_report_download_url(db: AsyncSession, user: models.User, **kwargs):
    result = await db.execute(
        select(models.Report).where(
            models.Report.id == kwargs["report_id"],
            models.Report.user_id == user.id,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        return {"error": "报告不存在或无权限"}
    return {
        "report_id": report.id, "format": report.format,
        "download_url": f"/api/v1/reports/{report.id}/download",
        "message": f"报告下载链接: /api/v1/reports/{report.id}/download",
    }


# ────────────────────────── Leaderboard ──────────────────────────

@registry.register(
    name="get_leaderboard",
    description="获取模型 ELO 排行榜，显示排名、得分、胜负场次和胜率",
    category="leaderboard",
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
)
async def get_leaderboard(db: AsyncSession, user: models.User, **kwargs):
    result = await db.execute(
        select(models.ModelEloScore)
        .join(models.ModelConfig, models.ModelEloScore.model_config_id == models.ModelConfig.id)
        .where(models.ModelConfig.user_id == user.id)
        .order_by(models.ModelEloScore.elo_score.desc())
    )
    scores = result.scalars().all()
    if not scores:
        return {"message": "暂无排行数据，请先运行包含多个模型的评测任务", "leaderboard": []}
    return {
        "leaderboard": [
            {
                "rank": i + 1,
                "model_name": s.model_name,
                "elo_score": round(s.elo_score, 1),
                "wins": s.wins, "losses": s.losses, "draws": s.draws,
                "total_matches": s.total_matches,
                "win_rate": round(s.wins / s.total_matches, 3) if s.total_matches > 0 else 0,
            }
            for i, s in enumerate(scores)
        ],
    }


@registry.register(
    name="get_benchmark_leaderboard",
    description="获取基准测试排行榜，按基准名称聚合各模型的历史评测分数",
    category="leaderboard",
    parameters={
        "type": "object",
        "properties": {
            "benchmark": {"type": "string", "description": "按基准名称过滤(可选)，如 mmlu_pro, gsm8k"},
        },
        "required": [],
    },
)
async def get_benchmark_leaderboard(db: AsyncSession, user: models.User, **kwargs):
    # Get completed tasks with benchmarks
    query = select(models.EvaluationTask).where(
        models.EvaluationTask.user_id == user.id,
        models.EvaluationTask.status == "completed",
        models.EvaluationTask.results_summary.isnot(None),
    )
    result = await db.execute(query)
    tasks = result.scalars().all()

    aggregated = {}
    for task in tasks:
        summary = task.results_summary or {}
        by_model = summary.get("by_model", {})
        for mid, data in by_model.items():
            model_name = data.get("model_name", f"Model {mid}")
            scores = data.get("scores", {})
            for score_key, score_val in scores.items():
                if kwargs.get("benchmark") and kwargs["benchmark"] not in score_key:
                    continue
                key = (model_name, score_key)
                if key not in aggregated:
                    aggregated[key] = []
                aggregated[key].append(score_val)

    leaderboard = []
    for (model_name, metric), vals in aggregated.items():
        leaderboard.append({
            "model_name": model_name,
            "metric": metric,
            "avg_score": round(sum(vals) / len(vals), 4),
            "runs": len(vals),
        })
    leaderboard.sort(key=lambda x: x["avg_score"], reverse=True)
    return {"leaderboard": leaderboard}


# ────────────────────────── Benchmarks ──────────────────────────

@registry.register(
    name="get_benchmarks",
    description="列出所有可用的标准基准测试（MMLU-Pro、GSM8K、HumanEval、C-Eval、HellaSwag、TruthfulQA、MATH、ARC、MT-Bench、AlpacaEval、IFEval、SWE-Bench、BigCodeBench、LiveBench），包括名称、描述、指标和样本量",
    category="benchmarks",
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
)
async def get_benchmarks(**kwargs):
    from app.api.v1.benchmarks import AVAILABLE_BENCHMARKS
    return {"benchmarks": AVAILABLE_BENCHMARKS}


# ────────────────────────── Navigation ──────────────────────────

@registry.register(
    name="navigate_to",
    description="跳转到平台指定页面。可用: dashboard(概览), models(模型), datasets(数据集), evaluations(评测列表), evaluations/new(新建评测), leaderboard(排行榜), benchmarks(基准), admin(管理). 也可跳转到带ID的详情页。",
    category="navigation",
    parameters={
        "type": "object",
        "properties": {
            "page": {
                "type": "string",
                "description": "页面名称",
                "enum": [
                    "dashboard", "models", "datasets",
                    "evaluations", "evaluations/new",
                    "leaderboard", "benchmarks", "admin",
                    "comparison", "prompts", "arena", "teams",
                    "settings/api-keys", "results", "optimize",
                ],
            },
            "entity_id": {"type": "integer", "description": "实体ID(可选)，用于跳转到详情页如 evaluations/123、results/123 或 optimize (评测优化页)"},
        },
        "required": ["page"],
    },
)
async def navigate_to(**kwargs):
    page = kwargs["page"]
    entity_id = kwargs.get("entity_id")
    path = f"/{page}"
    if entity_id:
        if page == "evaluations":
            path = f"/evaluations/{entity_id}"
        elif page == "results":
            path = f"/results/{entity_id}"
        elif page == "optimize":
            path = f"/evaluations/{entity_id}/optimize"
    return {"navigate": path, "message": f"正在跳转到 {path}"}


# ────────────────────────── Admin ──────────────────────────

@registry.register(
    name="get_platform_stats",
    description="获取平台整体统计数据：用户数、模型数、数据集数、评测任务数和完成率",
    category="admin",
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
)
async def get_platform_stats(db: AsyncSession, user: models.User, **kwargs):
    # Non-admin users get their own stats
    if user.is_admin:
        user_count = (await db.execute(select(func.count(models.User.id)))).scalar()
        model_count = (await db.execute(select(func.count(models.ModelConfig.id)))).scalar()
        dataset_count = (await db.execute(select(func.count(models.Dataset.id)))).scalar()
        task_count = (await db.execute(select(func.count(models.EvaluationTask.id)))).scalar()
        completed = (await db.execute(
            select(func.count(models.EvaluationTask.id)).where(models.EvaluationTask.status == "completed")
        )).scalar()
        return {
            "scope": "platform",
            "total_users": user_count, "total_models": model_count,
            "total_datasets": dataset_count, "total_evaluations": task_count,
            "completed_evaluations": completed,
            "completion_rate": f"{round(completed / task_count * 100)}%" if task_count > 0 else "0%",
        }
    else:
        model_count = (await db.execute(
            select(func.count(models.ModelConfig.id)).where(models.ModelConfig.user_id == user.id)
        )).scalar()
        dataset_count = (await db.execute(
            select(func.count(models.Dataset.id)).where(models.Dataset.user_id == user.id)
        )).scalar()
        task_count = (await db.execute(
            select(func.count(models.EvaluationTask.id)).where(models.EvaluationTask.user_id == user.id)
        )).scalar()
        completed = (await db.execute(
            select(func.count(models.EvaluationTask.id)).where(
                models.EvaluationTask.user_id == user.id,
                models.EvaluationTask.status == "completed",
            )
        )).scalar()
        return {
            "scope": "personal",
            "my_models": model_count, "my_datasets": dataset_count,
            "my_evaluations": task_count, "completed_evaluations": completed,
        }


@registry.register(
    name="list_users",
    description="列出平台所有用户（仅管理员可用）",
    category="admin",
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
)
async def list_users(db: AsyncSession, user: models.User, **kwargs):
    if not user.is_admin:
        return {"error": "需要管理员权限"}
    result = await db.execute(select(models.User))
    rows = result.scalars().all()
    return {
        "total": len(rows),
        "users": [
            {
                "id": u.id, "username": u.username, "email": u.email,
                "full_name": u.full_name, "is_admin": u.is_admin,
                "is_active": u.is_active, "created_at": u.created_at.isoformat(),
            }
            for u in rows
        ],
    }


@registry.register(
    name="toggle_user_active",
    description="启用或禁用指定用户（仅管理员可用）",
    category="admin",
    parameters={
        "type": "object",
        "properties": {
            "user_id": {"type": "integer", "description": "用户ID"},
        },
        "required": ["user_id"],
    },
    requires_confirmation=True,
)
async def toggle_user_active(db: AsyncSession, user: models.User, **kwargs):
    if not user.is_admin:
        return {"error": "需要管理员权限"}
    result = await db.execute(
        select(models.User).where(models.User.id == kwargs["user_id"])
    )
    target = result.scalar_one_or_none()
    if not target:
        return {"error": "用户不存在"}
    target.is_active = not target.is_active
    await db.flush()
    status = "启用" if target.is_active else "禁用"
    return {"message": f"用户 '{target.username}' 已{status}", "is_active": target.is_active}


# ────────────────────────── Retry ──────────────────────────

@registry.register(
    name="retry_evaluation",
    description="重试一个失败或已取消的评测任务，从上次检查点继续",
    category="evaluations",
    parameters={
        "type": "object",
        "properties": {
            "task_id": {"type": "integer", "description": "要重试的评测任务ID"},
        },
        "required": ["task_id"],
    },
    requires_confirmation=True,
)
async def retry_evaluation(db: AsyncSession, user: models.User, **kwargs):
    result = await db.execute(
        select(models.EvaluationTask).where(
            models.EvaluationTask.id == kwargs["task_id"],
            models.EvaluationTask.user_id == user.id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        return {"error": "评测任务不存在或无权限"}
    if task.status not in ("failed", "cancelled"):
        return {"error": f"只能重试失败或已取消的任务 (当前状态: {task.status})"}

    task.status = "pending"
    task.error_message = None
    task.retry_count = (task.retry_count or 0) + 1
    await db.flush()

    # Commit BEFORE dispatching Celery to avoid race condition
    await db.commit()

    from app.services.evaluation import run_evaluation_task
    celery_result = run_evaluation_task.delay(task.id)
    task.celery_task_id = celery_result.id
    await db.flush()

    return {
        "id": task.id, "name": task.name, "status": "pending",
        "retry_count": task.retry_count,
        "message": f"评测任务 '{task.name}' 已重新提交 (第 {task.retry_count} 次重试)",
        "navigate": f"/evaluations/{task.id}",
    }


# ────────────────────────── Audit ──────────────────────────

@registry.register(
    name="get_audit_logs",
    description="查询系统操作审计日志（仅管理员可用），可按操作类型、用户ID过滤",
    category="admin",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "按操作类型过滤，如 user.login, evaluation.create, model.delete"},
            "user_id": {"type": "integer", "description": "按用户ID过滤"},
            "limit": {"type": "integer", "description": "返回条数(默认20)", "default": 20},
        },
        "required": [],
    },
)
async def get_audit_logs(db: AsyncSession, user: models.User, **kwargs):
    if not user.is_admin:
        return {"error": "需要管理员权限"}

    from app.db.models import AuditLog
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    if kwargs.get("action"):
        query = query.where(AuditLog.action == kwargs["action"])
    if kwargs.get("user_id"):
        query = query.where(AuditLog.user_id == kwargs["user_id"])
    query = query.limit(kwargs.get("limit", 20))

    result = await db.execute(query)
    logs = result.scalars().all()
    return {
        "total": len(logs),
        "logs": [
            {
                "id": l.id, "user_id": l.user_id, "action": l.action,
                "resource_type": l.resource_type, "resource_id": l.resource_id,
                "details": l.details, "ip_address": l.ip_address,
                "created_at": l.created_at.isoformat(),
            }
            for l in logs
        ],
    }


# ────────────────────────── Prompts ──────────────────────────

@registry.register(
    name="list_prompt_templates",
    description="列出当前用户的提示词模板，支持按类型和领域筛选。类型分为 generation（生成提示词）和 evaluation（评测提示词）",
    category="prompts",
    parameters={
        "type": "object",
        "properties": {
            "prompt_type": {"type": "string", "enum": ["generation", "evaluation"], "description": "筛选提示词类型(可选)"},
            "domain": {"type": "string", "description": "筛选领域(可选)，预设值: medical/finance/industrial/legal/education/general，也支持自定义领域名"},
        },
        "required": [],
    },
)
async def list_prompt_templates(db: AsyncSession, user: models.User, **kwargs):
    query = select(models.PromptTemplate).where(
        models.PromptTemplate.user_id == user.id
    ).order_by(models.PromptTemplate.created_at.desc())
    if kwargs.get("prompt_type"):
        query = query.where(models.PromptTemplate.prompt_type == kwargs["prompt_type"])
    if kwargs.get("domain"):
        query = query.where(models.PromptTemplate.domain == kwargs["domain"])
    result = await db.execute(query)
    rows = result.scalars().all()
    return {
        "total": len(rows),
        "templates": [
            {
                "id": t.id, "name": t.name,
                "content_preview": (t.content or "")[:100],
                "variables": t.variables or [],
                "version": t.version,
                "parent_id": t.parent_id,
                "tags": t.tags or [],
                "prompt_type": t.prompt_type or "generation",
                "domain": t.domain,
                "is_active": t.is_active,
                "created_at": t.created_at.isoformat(),
            }
            for t in rows
        ],
    }


@registry.register(
    name="create_prompt_template",
    description="创建一个新的提示词模板。使用 {{变量名}} 语法定义模板变量。prompt_type='generation' 用于给被测模型的生成提示词，'evaluation' 用于给上位评判模型的评测提示词。",
    category="prompts",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "模板名称"},
            "content": {"type": "string", "description": "提示词内容，支持 {{var}} 变量语法"},
            "variables": {"type": "array", "items": {"type": "string"}, "description": "变量名列表(可选)"},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "标签列表(可选)"},
            "prompt_type": {"type": "string", "enum": ["generation", "evaluation"], "description": "提示词类型: generation(生成) 或 evaluation(评测)，默认generation"},
            "domain": {"type": "string", "description": "领域标识(可选)，预设: medical/finance/industrial/legal/education/general，也支持自定义"},
        },
        "required": ["name", "content"],
    },
)
async def create_prompt_template(db: AsyncSession, user: models.User, **kwargs):
    template = models.PromptTemplate(
        user_id=user.id,
        name=kwargs["name"],
        content=kwargs["content"],
        variables=kwargs.get("variables", []),
        tags=kwargs.get("tags", []),
        version=1,
        prompt_type=kwargs.get("prompt_type", "generation"),
        domain=kwargs.get("domain"),
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return {
        "id": template.id,
        "name": template.name,
        "prompt_type": template.prompt_type,
        "domain": template.domain,
        "version": template.version,
        "message": f"提示词模板 '{template.name}' 已创建 (ID: {template.id}, 类型: {template.prompt_type})",
        "navigate": "/prompts",
    }


@registry.register(
    name="get_prompt_template",
    description="获取指定提示词模板的完整内容",
    category="prompts",
    parameters={
        "type": "object",
        "properties": {
            "template_id": {"type": "integer", "description": "模板ID"},
        },
        "required": ["template_id"],
    },
)
async def get_prompt_template(db: AsyncSession, user: models.User, **kwargs):
    result = await db.execute(
        select(models.PromptTemplate).where(
            models.PromptTemplate.id == kwargs["template_id"],
            models.PromptTemplate.user_id == user.id,
        )
    )
    t = result.scalar_one_or_none()
    if not t:
        return {"error": "模板不存在或无权限"}
    return {
        "id": t.id, "name": t.name, "content": t.content,
        "variables": t.variables or [], "tags": t.tags or [],
        "prompt_type": t.prompt_type, "domain": t.domain,
        "version": t.version, "is_active": t.is_active,
    }


@registry.register(
    name="update_prompt_template",
    description="更新提示词模板的名称、内容、变量、标签、类型或领域。内容变更会自动升版本号。",
    category="prompts",
    parameters={
        "type": "object",
        "properties": {
            "template_id": {"type": "integer", "description": "模板ID"},
            "name": {"type": "string", "description": "新名称(可选)"},
            "content": {"type": "string", "description": "新内容(可选)"},
            "variables": {"type": "array", "items": {"type": "string"}, "description": "新变量列表(可选)"},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "新标签列表(可选)"},
            "prompt_type": {"type": "string", "enum": ["generation", "evaluation"], "description": "新类型(可选)"},
            "domain": {"type": "string", "description": "新领域(可选)"},
            "is_active": {"type": "boolean", "description": "是否激活(可选)"},
        },
        "required": ["template_id"],
    },
)
async def update_prompt_template(db: AsyncSession, user: models.User, **kwargs):
    result = await db.execute(
        select(models.PromptTemplate).where(
            models.PromptTemplate.id == kwargs["template_id"],
            models.PromptTemplate.user_id == user.id,
        )
    )
    t = result.scalar_one_or_none()
    if not t:
        return {"error": "模板不存在或无权限"}
    content_changed = False
    if "name" in kwargs and kwargs["name"] is not None:
        t.name = kwargs["name"]
    if "content" in kwargs and kwargs["content"] is not None:
        if t.content != kwargs["content"]:
            content_changed = True
        t.content = kwargs["content"]
    if "variables" in kwargs:
        t.variables = kwargs["variables"]
    if "tags" in kwargs:
        t.tags = kwargs["tags"]
    if "prompt_type" in kwargs:
        t.prompt_type = kwargs["prompt_type"]
    if "domain" in kwargs:
        t.domain = kwargs["domain"]
    if "is_active" in kwargs:
        t.is_active = kwargs["is_active"]
    if content_changed:
        t.version = (t.version or 1) + 1
    await db.flush()
    await db.refresh(t)
    return {
        "id": t.id, "name": t.name, "version": t.version,
        "message": f"模板 '{t.name}' 已更新" + (f" (版本升至 v{t.version})" if content_changed else ""),
    }


@registry.register(
    name="delete_prompt_template",
    description="删除指定的提示词模板（不可恢复）",
    category="prompts",
    parameters={
        "type": "object",
        "properties": {
            "template_id": {"type": "integer", "description": "模板ID"},
        },
        "required": ["template_id"],
    },
    requires_confirmation=True,
)
async def delete_prompt_template(db: AsyncSession, user: models.User, **kwargs):
    result = await db.execute(
        select(models.PromptTemplate).where(
            models.PromptTemplate.id == kwargs["template_id"],
            models.PromptTemplate.user_id == user.id,
        )
    )
    t = result.scalar_one_or_none()
    if not t:
        return {"error": "模板不存在或无权限"}
    name = t.name
    await db.delete(t)
    await db.flush()
    return {"message": f"模板 '{name}' (ID: {kwargs['template_id']}) 已删除"}


@registry.register(
    name="delete_evaluation",
    description="永久删除指定的评测任务及其所有结果（不可恢复）",
    category="evaluations",
    parameters={
        "type": "object",
        "properties": {
            "task_id": {"type": "integer", "description": "评测任务ID"},
        },
        "required": ["task_id"],
    },
    requires_confirmation=True,
)
async def delete_evaluation_tool(db: AsyncSession, user: models.User, **kwargs):
    from sqlalchemy import delete as sql_delete
    result = await db.execute(
        select(models.EvaluationTask).where(
            models.EvaluationTask.id == kwargs["task_id"],
            models.EvaluationTask.user_id == user.id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        return {"error": "任务不存在或无权限"}
    name = task.name
    # Cancel if running
    if task.status in ("pending", "running") and task.celery_task_id:
        try:
            from app.core.celery_app import celery_app
            celery_app.control.revoke(task.celery_task_id, terminate=True)
        except Exception:
            pass
    # Clean up all associated records
    await db.execute(sql_delete(models.EvaluationResult).where(models.EvaluationResult.task_id == task.id))
    try:
        await db.execute(sql_delete(models.GeneratedTrainingData).where(models.GeneratedTrainingData.task_id == task.id))
    except Exception:
        pass
    await db.execute(sql_delete(models.Report).where(models.Report.task_id == task.id))
    await db.execute(sql_delete(models.TaskModelAssociation).where(models.TaskModelAssociation.task_id == task.id))
    await db.delete(task)
    await db.flush()
    return {"message": f"评测任务 '{name}' (ID: {kwargs['task_id']}) 及所有结果已删除"}


@registry.register(
    name="batch_delete_evaluations",
    description="批量删除多个评测任务及其所有结果（不可恢复）",
    category="evaluations",
    parameters={
        "type": "object",
        "properties": {
            "task_ids": {"type": "array", "items": {"type": "integer"}, "description": "评测任务ID列表"},
        },
        "required": ["task_ids"],
    },
    requires_confirmation=True,
)
async def batch_delete_evaluations_tool(db: AsyncSession, user: models.User, **kwargs):
    from sqlalchemy import delete as sql_delete
    result = await db.execute(
        select(models.EvaluationTask).where(
            models.EvaluationTask.id.in_(kwargs["task_ids"]),
            models.EvaluationTask.user_id == user.id,
        )
    )
    tasks = result.scalars().all()
    if not tasks:
        return {"error": "未找到匹配的任务"}
    deleted = []
    for task in tasks:
        if task.status in ("pending", "running") and task.celery_task_id:
            try:
                from app.core.celery_app import celery_app
                celery_app.control.revoke(task.celery_task_id, terminate=True)
            except Exception:
                pass
        await db.execute(sql_delete(models.EvaluationResult).where(models.EvaluationResult.task_id == task.id))
        try:
            await db.execute(sql_delete(models.GeneratedTrainingData).where(models.GeneratedTrainingData.task_id == task.id))
        except Exception:
            pass
        await db.execute(sql_delete(models.Report).where(models.Report.task_id == task.id))
        await db.execute(sql_delete(models.TaskModelAssociation).where(models.TaskModelAssociation.task_id == task.id))
        await db.delete(task)
        deleted.append(task.id)
    await db.flush()
    return {"deleted": len(deleted), "ids": deleted, "message": f"已删除 {len(deleted)} 个评测任务"}


@registry.register(
    name="list_judge_models",
    description="列出当前用户配置的裁判模型",
    category="models",
    parameters={"type": "object", "properties": {}, "required": []},
)
async def list_judge_models(db: AsyncSession, user: models.User, **kwargs):
    result = await db.execute(
        select(models.JudgeModelConfig).where(models.JudgeModelConfig.user_id == user.id)
    )
    rows = result.scalars().all()
    return {
        "total": len(rows),
        "judge_models": [
            {
                "id": m.id, "name": m.name, "provider": m.provider,
                "model_name": m.model_name, "base_url": m.base_url,
                "is_default": m.is_default, "is_active": m.is_active,
            }
            for m in rows
        ],
    }


@registry.register(
    name="create_judge_model",
    description="创建一个裁判模型配置，用于 LLM-Judge 评测和垂直领域评测的评分",
    category="models",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "裁判模型名称"},
            "provider": {"type": "string", "description": "服务商: openai/anthropic/custom 等"},
            "model_name": {"type": "string", "description": "模型标识符"},
            "api_key": {"type": "string", "description": "API Key(可选)"},
            "base_url": {"type": "string", "description": "API 地址(可选)"},
            "is_default": {"type": "boolean", "description": "是否设为默认裁判模型"},
        },
        "required": ["name", "provider", "model_name"],
    },
)
async def create_judge_model(db: AsyncSession, user: models.User, **kwargs):
    encrypted_key = None
    if kwargs.get("api_key"):
        encrypted_key = encrypt_api_key(kwargs["api_key"])
    jm = models.JudgeModelConfig(
        user_id=user.id,
        name=kwargs["name"],
        provider=kwargs["provider"],
        model_name=kwargs["model_name"],
        api_key_encrypted=encrypted_key,
        base_url=kwargs.get("base_url"),
        is_default=kwargs.get("is_default", False),
    )
    db.add(jm)
    await db.flush()
    await db.refresh(jm)
    return {
        "id": jm.id, "name": jm.name,
        "message": f"裁判模型 '{jm.name}' 已创建 (ID: {jm.id})",
    }


@registry.register(
    name="run_prompt_experiment",
    description="创建并运行提示词 A/B 实验：选择多个提示词模板和模型，用测试数据运行对比。用于在正式评测前验证提示词效果。返回实验ID，可在提示词实验页面查看完整结果。",
    category="prompts",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "实验名称"},
            "template_ids": {"type": "array", "items": {"type": "integer"}, "description": "提示词模板ID列表"},
            "model_ids": {"type": "array", "items": {"type": "integer"}, "description": "模型ID列表"},
            "test_inputs": {"type": "array", "items": {"type": "object"}, "description": "测试数据列表，如 [{\"input\": \"问题1\"}, {\"input\": \"问题2\"}]"},
        },
        "required": ["name", "template_ids", "model_ids", "test_inputs"],
    },
)
async def run_prompt_experiment(db: AsyncSession, user: models.User, **kwargs):
    # Create experiment record
    exp = models.PromptExperiment(
        user_id=user.id,
        name=kwargs["name"],
        template_ids=kwargs["template_ids"],
        model_ids=kwargs["model_ids"],
        test_inputs=kwargs["test_inputs"],
        status="pending",
    )
    db.add(exp)
    await db.flush()
    await db.refresh(exp)
    return {
        "experiment_id": exp.id,
        "status": "pending",
        "message": f"实验 '{exp.name}' 已创建 (ID: {exp.id})，请前往提示词实验页面点击运行查看结果",
        "navigate": "/prompts/experiment",
    }


# ────────────────────────── Analysis (6 tools) ──────────────────────────

@registry.register(
    name="compare_evaluations",
    description="对比分析多个评测任务的结果，返回各模型在不同维度上的得分对比、平均延迟和样本数",
    category="analysis",
    parameters={
        "type": "object",
        "properties": {
            "task_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "要对比的评测任务ID列表（2-5个）",
            },
        },
        "required": ["task_ids"],
    },
)
async def compare_evaluations(db: AsyncSession, user: models.User, **kwargs):
    task_ids = kwargs["task_ids"]
    if len(task_ids) < 2:
        return {"error": "至少需要2个任务进行对比"}

    tasks = []
    for tid in task_ids:
        result = await db.execute(
            select(models.EvaluationTask).where(
                models.EvaluationTask.id == tid,
                models.EvaluationTask.user_id == user.id,
            )
        )
        task = result.scalar_one_or_none()
        if task:
            tasks.append(task)

    if len(tasks) < 2:
        return {"error": "找不到足够的评测任务"}

    comparison = {}
    score_keys = set()
    for task in tasks:
        summary = task.results_summary or {}
        by_model = summary.get("by_model", {})
        for mid, data in by_model.items():
            model_name = data.get("model_name", f"Model {mid}")
            scores = data.get("scores", {})
            score_keys.update(scores.keys())
            if model_name not in comparison:
                comparison[model_name] = {"scores": {}, "avg_latency_ms": 0, "sample_count": 0}
            for k, v in scores.items():
                if k not in comparison[model_name]["scores"]:
                    comparison[model_name]["scores"][k] = []
                comparison[model_name]["scores"][k].append(v)
            comparison[model_name]["avg_latency_ms"] = data.get("avg_latency_ms", 0)
            comparison[model_name]["sample_count"] += data.get("sample_count", 0)

    # Average scores
    for model_name in comparison:
        for k in comparison[model_name]["scores"]:
            vals = comparison[model_name]["scores"][k]
            comparison[model_name]["scores"][k] = round(sum(vals) / len(vals), 4) if vals else 0

    return {
        "tasks": [{"id": t.id, "name": t.name, "status": t.status} for t in tasks],
        "by_model": comparison,
        "score_keys": sorted(score_keys),
    }


@registry.register(
    name="analyze_failures",
    description="分析评测任务中的失败案例，聚类常见错误类型，帮助发现模型薄弱环节",
    category="analysis",
    parameters={
        "type": "object",
        "properties": {
            "task_id": {"type": "integer", "description": "评测任务ID"},
            "model_id": {"type": "integer", "description": "模型ID（可选，过滤特定模型）"},
            "threshold": {"type": "number", "description": "低分阈值（默认0.5），低于此分的结果视为失败", "default": 0.5},
        },
        "required": ["task_id"],
    },
)
async def analyze_failures(db: AsyncSession, user: models.User, **kwargs):
    task_id = kwargs["task_id"]
    threshold = kwargs.get("threshold", 0.5)

    result = await db.execute(
        select(models.EvaluationTask).where(
            models.EvaluationTask.id == task_id,
            models.EvaluationTask.user_id == user.id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        return {"error": "评测任务不存在"}

    query = select(models.EvaluationResult).where(
        models.EvaluationResult.task_id == task_id
    )
    if kwargs.get("model_id"):
        query = query.where(models.EvaluationResult.model_id == kwargs["model_id"])

    result = await db.execute(query)
    all_results = result.scalars().all()

    failures = []
    error_types = {}
    for r in all_results:
        scores = r.scores or {}
        avg_score = sum(scores.values()) / len(scores) if scores else 0
        if avg_score < threshold:
            failures.append({
                "sample_index": r.sample_index,
                "model_id": r.model_id,
                "input_preview": (r.input_text or "")[:100],
                "output_preview": (r.output_text or "")[:100],
                "scores": scores,
                "avg_score": round(avg_score, 4),
            })
            # Cluster by lowest scoring dimension
            if scores:
                worst = min(scores, key=scores.get)
                error_types[worst] = error_types.get(worst, 0) + 1

    return {
        "task_name": task.name,
        "total_results": len(all_results),
        "failure_count": len(failures),
        "failure_rate": round(len(failures) / len(all_results), 4) if all_results else 0,
        "error_type_distribution": dict(sorted(error_types.items(), key=lambda x: x[1], reverse=True)),
        "worst_cases": sorted(failures, key=lambda x: x["avg_score"])[:10],
    }


@registry.register(
    name="suggest_evaluation_config",
    description="根据用户的模型和数据集情况，智能推荐评测配置（维度、基准测试等）",
    category="analysis",
    parameters={
        "type": "object",
        "properties": {
            "model_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "要评测的模型ID列表",
            },
            "dataset_id": {"type": "integer", "description": "数据集ID（可选）"},
            "goal": {"type": "string", "description": "评测目标，如 '全面评测'、'代码能力'、'安全性测试'、'性能基准'"},
        },
        "required": ["model_ids"],
    },
)
async def suggest_evaluation_config(db: AsyncSession, user: models.User, **kwargs):
    model_ids = kwargs["model_ids"]
    goal = kwargs.get("goal", "全面评测")
    dataset_id = kwargs.get("dataset_id")

    # Get model info
    model_infos = []
    for mid in model_ids:
        result = await db.execute(
            select(models.ModelConfig).where(
                models.ModelConfig.id == mid,
                models.ModelConfig.user_id == user.id,
            )
        )
        m = result.scalar_one_or_none()
        if m:
            model_infos.append({"id": m.id, "name": m.name, "provider": m.provider})

    # Get dataset info
    dataset_info = None
    if dataset_id:
        result = await db.execute(
            select(models.Dataset).where(models.Dataset.id == dataset_id)
        )
        ds = result.scalar_one_or_none()
        if ds:
            dataset_info = {"id": ds.id, "name": ds.name, "category": ds.category, "size": ds.size}

    # Build config recommendation
    config = {"performance": True}
    benchmarks = []
    reasons = []

    if "代码" in goal or (dataset_info and dataset_info.get("category") == "code"):
        config["code_execution"] = True
        benchmarks.extend(["humaneval", "bigcodebench"])
        reasons.append("检测到代码相关需求，启用代码执行评测和HumanEval基准")
    if "安全" in goal:
        config["safety"] = True
        config["robustness"] = True
        config["robustness_perturbations"] = ["typo", "paraphrase", "negation"]
        reasons.append("启用安全性和鲁棒性测试")
    if "全面" in goal:
        config.update({
            "performance": True, "hallucination": True,
            "consistency": True, "instruction_following": True,
            "cot_reasoning": True,
        })
        benchmarks.extend(["mmlu_pro", "gsm8k", "truthfulqa"])
        reasons.append("全面评测：启用性能、幻觉检测、一致性、指令跟随、推理链")
    if "性能" in goal or "基准" in goal:
        benchmarks.extend(["mmlu_pro", "gsm8k", "humaneval", "ceval", "hellaswag"])
        reasons.append("基准测试：添加MMLU-Pro、GSM8K、HumanEval、C-Eval、HellaSwag")
    if len(model_ids) >= 2:
        reasons.append(f"多模型对比：{len(model_ids)} 个模型将参与评测，完成后可对比分析")

    if benchmarks:
        config["benchmarks"] = list(set(benchmarks))

    return {
        "models": model_infos,
        "dataset": dataset_info,
        "goal": goal,
        "recommended_config": config,
        "reasons": reasons,
        "suggested_name": f"{goal} - {', '.join(m['name'] for m in model_infos[:3])}",
    }


@registry.register(
    name="estimate_cost",
    description="预估评测任务的token消耗和费用",
    category="analysis",
    parameters={
        "type": "object",
        "properties": {
            "model_ids": {"type": "array", "items": {"type": "integer"}, "description": "模型ID列表"},
            "sample_count": {"type": "integer", "description": "样本数量"},
            "avg_input_tokens": {"type": "integer", "description": "预估平均输入token数(默认200)", "default": 200},
            "avg_output_tokens": {"type": "integer", "description": "预估平均输出token数(默认300)", "default": 300},
        },
        "required": ["model_ids", "sample_count"],
    },
)
async def estimate_cost(db: AsyncSession, user: models.User, **kwargs):
    model_ids = kwargs["model_ids"]
    sample_count = kwargs["sample_count"]
    avg_input = kwargs.get("avg_input_tokens", 200)
    avg_output = kwargs.get("avg_output_tokens", 300)

    PRICING = {
        "gpt-4o": (2.5, 10.0),
        "gpt-4o-mini": (0.15, 0.6),
        "gpt-4-turbo": (10.0, 30.0),
        "gpt-3.5-turbo": (0.5, 1.5),
        "claude-3-opus": (15.0, 75.0),
        "claude-3-sonnet": (3.0, 15.0),
        "claude-3-haiku": (0.25, 1.25),
        "claude-3.5-sonnet": (3.0, 15.0),
    }

    estimates = []
    total_cost = 0
    for mid in model_ids:
        result = await db.execute(
            select(models.ModelConfig).where(
                models.ModelConfig.id == mid,
                models.ModelConfig.user_id == user.id,
            )
        )
        m = result.scalar_one_or_none()
        if not m:
            continue

        pricing = None
        for key, val in PRICING.items():
            if key in m.model_name.lower():
                pricing = val
                break

        total_tokens_in = sample_count * avg_input
        total_tokens_out = sample_count * avg_output
        if pricing:
            cost = (total_tokens_in / 1_000_000 * pricing[0]) + (total_tokens_out / 1_000_000 * pricing[1])
        else:
            cost = (total_tokens_in + total_tokens_out) / 1_000_000 * 2.0  # default estimate

        estimates.append({
            "model": m.name,
            "model_name": m.model_name,
            "total_input_tokens": total_tokens_in,
            "total_output_tokens": total_tokens_out,
            "estimated_cost_usd": round(cost, 4),
            "pricing_known": pricing is not None,
        })
        total_cost += cost

    return {
        "sample_count": sample_count,
        "avg_input_tokens": avg_input,
        "avg_output_tokens": avg_output,
        "estimates": estimates,
        "total_estimated_cost_usd": round(total_cost, 4),
        "estimated_time_minutes": round(sample_count * len(model_ids) * 2 / 60, 1),  # ~2s per sample
    }


@registry.register(
    name="explain_scores",
    description="解读评测分数含义，给出改进建议。输入评测任务ID，返回各维度得分解读和优化方向",
    category="analysis",
    parameters={
        "type": "object",
        "properties": {
            "task_id": {"type": "integer", "description": "评测任务ID"},
        },
        "required": ["task_id"],
    },
)
async def explain_scores(db: AsyncSession, user: models.User, **kwargs):
    result = await db.execute(
        select(models.EvaluationTask).where(
            models.EvaluationTask.id == kwargs["task_id"],
            models.EvaluationTask.user_id == user.id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        return {"error": "评测任务不存在"}
    if task.status != "completed":
        return {"error": f"任务尚未完成 (当前状态: {task.status})"}

    summary = task.results_summary or {}
    by_model = summary.get("by_model", {})

    SCORE_EXPLANATIONS = {
        "accuracy": ("准确率", "模型输出与参考答案的匹配程度", "优化提示词、增加few-shot示例、使用更大参数模型"),
        "fluency": ("流畅性", "文本的语法正确性和可读性", "微调训练数据质量、调整temperature参数"),
        "relevance": ("相关性", "回复与问题的相关程度", "改进提示词使其更具体，增加上下文信息"),
        "coherence": ("连贯性", "文本逻辑连贯和前后一致性", "使用思维链(CoT)提示，适当增加max_tokens"),
        "hallucination_score": ("幻觉得分", "模型生成虚假信息的倾向(越高越好)", "使用RAG增加事实依据，降低temperature"),
        "safety_score": ("安全得分", "模型拒绝有害请求的能力", "增加安全系统提示，微调安全对齐"),
        "instruction_following": ("指令跟随", "严格遵循指令格式和约束的能力", "优化指令清晰度，使用结构化提示"),
        "cot_quality": ("推理质量", "思维链推理的完整性和正确性", "在提示中要求逐步思考，使用更大模型"),
        "code_pass_rate": ("代码通过率", "生成代码通过测试用例的比例", "提供更多代码上下文，使用代码专用模型"),
    }

    explanations = {}
    for mid, data in by_model.items():
        model_name = data.get("model_name", f"Model {mid}")
        scores = data.get("scores", {})
        model_exp = {}
        for key, val in scores.items():
            base_key = key.split("_avg")[0] if "_avg" in key else key
            info = SCORE_EXPLANATIONS.get(base_key, (key, "评测指标", "请参考相关文档"))
            level = "excellent" if val >= 0.85 else "good" if val >= 0.7 else "fair" if val >= 0.5 else "poor"
            model_exp[key] = {
                "score": round(val, 4),
                "label": info[0],
                "meaning": info[1],
                "level": level,
                "suggestion": info[2] if level in ("fair", "poor") else "当前表现良好",
            }
        explanations[model_name] = model_exp

    return {
        "task_name": task.name,
        "explanations": explanations,
    }


@registry.register(
    name="save_memory",
    description="保存一条用户偏好或上下文记忆，帮助AI助手在后续对话中提供个性化服务",
    category="analysis",
    parameters={
        "type": "object",
        "properties": {
            "memory_type": {
                "type": "string",
                "description": "记忆类型",
                "enum": ["preference", "context", "insight"],
            },
            "key": {"type": "string", "description": "记忆键，简短描述，如 '常用模型'、'评测偏好'"},
            "value": {"type": "string", "description": "记忆内容"},
        },
        "required": ["memory_type", "key", "value"],
    },
)
async def save_memory(db: AsyncSession, user: models.User, **kwargs):
    # Check if similar memory exists
    result = await db.execute(
        select(models.AgentMemory).where(
            models.AgentMemory.user_id == user.id,
            models.AgentMemory.key == kwargs["key"],
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.value = kwargs["value"]
        existing.memory_type = kwargs["memory_type"]
        await db.flush()
        return {"message": f"已更新记忆: {kwargs['key']}", "id": existing.id}

    mem = models.AgentMemory(
        user_id=user.id,
        memory_type=kwargs["memory_type"],
        key=kwargs["key"],
        value=kwargs["value"],
    )
    db.add(mem)
    await db.flush()
    await db.refresh(mem)
    return {"message": f"已保存记忆: {kwargs['key']}", "id": mem.id}


# ────────────────────────── Skills (High-level workflows) ──────────────────────────

@registry.register(
    name="quick_model_test",
    description="快速测试一个模型：给定模型ID和一个问题，直接调用模型API获取回复。用于快速验证模型是否正常工作。",
    category="skills",
    parameters={
        "type": "object",
        "properties": {
            "model_id": {"type": "integer", "description": "模型配置ID"},
            "prompt": {"type": "string", "description": "要发送给模型的问题/提示"},
            "max_tokens": {"type": "integer", "description": "最大回复token数(默认256)", "default": 256},
        },
        "required": ["model_id", "prompt"],
    },
)
async def quick_model_test(db: AsyncSession, user: models.User, **kwargs):
    from app.core.security import decrypt_api_key
    from app.core.http import make_async_httpx_client
    import time

    result = await db.execute(
        select(models.ModelConfig).where(
            models.ModelConfig.id == kwargs["model_id"],
            models.ModelConfig.user_id == user.id,
        )
    )
    model = result.scalar_one_or_none()
    if not model:
        return {"error": "模型不存在或无权限"}

    api_key = decrypt_api_key(model.api_key_encrypted) if model.api_key_encrypted else None
    if not api_key:
        return {"error": "模型未配置API密钥"}

    base_url = model.base_url or "https://api.openai.com/v1"
    url = f"{base_url}/chat/completions"
    max_tokens = kwargs.get("max_tokens", 256)

    try:
        start = time.time()
        async with make_async_httpx_client(timeout=60.0) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model.model_name,
                    "messages": [{"role": "user", "content": kwargs["prompt"]}],
                    "max_tokens": max_tokens,
                },
            )
        latency = round((time.time() - start) * 1000)

        if resp.status_code == 200:
            data = resp.json()
            reply = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return {
                "model": model.name,
                "prompt": kwargs["prompt"],
                "reply": reply,
                "latency_ms": latency,
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
            }
        else:
            return {"error": f"API请求失败: HTTP {resp.status_code} - {resp.text[:200]}"}
    except Exception as e:
        return {"error": f"请求错误: {str(e)}"}


@registry.register(
    name="get_my_overview",
    description="获取当前用户的完整概览：模型数量、数据集数量、评测任务状态分布、最近的评测任务等",
    category="skills",
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
)
async def get_my_overview(db: AsyncSession, user: models.User, **kwargs):
    model_count = (await db.execute(
        select(func.count(models.ModelConfig.id)).where(models.ModelConfig.user_id == user.id)
    )).scalar()
    dataset_count = (await db.execute(
        select(func.count(models.Dataset.id)).where(models.Dataset.user_id == user.id)
    )).scalar()

    # Task status distribution
    task_result = await db.execute(
        select(models.EvaluationTask.status, func.count(models.EvaluationTask.id))
        .where(models.EvaluationTask.user_id == user.id)
        .group_by(models.EvaluationTask.status)
    )
    status_dist = {row[0]: row[1] for row in task_result.all()}

    # Recent tasks
    recent_result = await db.execute(
        select(models.EvaluationTask)
        .where(models.EvaluationTask.user_id == user.id)
        .order_by(models.EvaluationTask.created_at.desc())
        .limit(5)
    )
    recent_tasks = recent_result.scalars().all()

    return {
        "user": user.username,
        "models_count": model_count,
        "datasets_count": dataset_count,
        "evaluations_by_status": status_dist,
        "total_evaluations": sum(status_dist.values()),
        "recent_tasks": [
            {"id": t.id, "name": t.name, "status": t.status, "progress": t.progress,
             "created_at": t.created_at.isoformat()}
            for t in recent_tasks
        ],
    }


# ────────────────────────── HealthBench ──────────────────────────

@registry.register(
    name="run_healthbench",
    description="快速运行 HealthBench 医疗健康评测基准。HealthBench 是 OpenAI 发布的医疗 LLM 评测，基于262位医生标注的5000个多轮对话，"
                "涵盖7大主题（全球健康、急诊转诊、不确定性应对、专业沟通、上下文获取、健康数据任务、回复深度）"
                "和5个评测维度（完整性、准确性、上下文感知、沟通质量、指令遵循）。"
                "支持三个变体：healthbench（完整版）、healthbench_hard（困难版）、healthbench_consensus（共识版）",
    category="skills",
    parameters={
        "type": "object",
        "properties": {
            "model_ids": {"type": "array", "items": {"type": "integer"}, "description": "参与评测的模型ID列表"},
            "variant": {
                "type": "string",
                "enum": ["healthbench", "healthbench_hard", "healthbench_consensus"],
                "description": "HealthBench变体：healthbench(完整版，默认)、healthbench_hard(困难版)、healthbench_consensus(共识版)",
            },
            "max_samples": {"type": "integer", "description": "最大评测样本数（可选）"},
        },
        "required": ["model_ids"],
    },
)
async def run_healthbench(db: AsyncSession, user: models.User, **kwargs):
    model_ids = kwargs["model_ids"]
    variant = kwargs.get("variant", "healthbench")
    max_samples = kwargs.get("max_samples")

    # Validate models
    for mid in model_ids:
        result = await db.execute(
            select(models.ModelConfig).where(
                models.ModelConfig.id == mid,
                models.ModelConfig.user_id == user.id,
            )
        )
        if not result.scalar_one_or_none():
            return {"error": f"模型 ID {mid} 不存在或无权限"}

    variant_names = {
        "healthbench": "HealthBench 完整版",
        "healthbench_hard": "HealthBench 困难版",
        "healthbench_consensus": "HealthBench 共识版",
    }

    evaluator_config = {
        "performance": True,
        "benchmarks": [variant],
    }
    if max_samples:
        evaluator_config["max_samples"] = max_samples

    task = models.EvaluationTask(
        user_id=user.id,
        name=f"{variant_names.get(variant, 'HealthBench')} 医疗评测",
        description=f"使用 {variant_names.get(variant, 'HealthBench')} 评测模型的医疗健康能力",
        model_ids=model_ids,
        evaluator_config=evaluator_config,
        status="pending",
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)

    # Commit BEFORE dispatching Celery to avoid race condition
    await db.commit()

    from app.services.evaluation import run_evaluation_task
    celery_result = run_evaluation_task.delay(task.id)
    task.celery_task_id = celery_result.id
    await db.flush()

    return {
        "id": task.id,
        "name": task.name,
        "status": task.status,
        "variant": variant,
        "message": f"HealthBench 医疗评测任务已创建并开始运行 (ID: {task.id})，使用 {variant_names.get(variant, variant)} 变体",
        "navigate": f"/evaluations/{task.id}",
    }


# ────────────────────────── Domain Evaluation (4 tools) ──────────────────────────

@registry.register(
    name="run_domain_evaluation",
    description="创建垂直领域评测任务。使用双Prompt模式：生成提示词发送给被测模型，评测提示词发送给上位评判模型进行打分和诊断。",
    category="domain_eval",
    parameters={
        "type": "object",
        "properties": {
            "model_ids": {"type": "array", "items": {"type": "integer"}, "description": "被测模型ID列表"},
            "domain": {"type": "string", "description": "评测领域，预设: medical/finance/industrial/legal/education/general，也支持自定义"},
            "generation_prompt_ids": {"type": "array", "items": {"type": "integer"}, "description": "生成提示词模板ID列表（给被测模型用的）"},
            "evaluation_prompt_ids": {"type": "array", "items": {"type": "integer"}, "description": "评测提示词模板ID列表（给上位评判模型用的）"},
            "judge_model_id": {"type": "integer", "description": "上位评判模型ID"},
            "dataset_id": {"type": "integer", "description": "评测数据集ID(可选)"},
            "eval_mode": {"type": "string", "enum": ["evaluate", "evaluate_optimize"], "description": "评测模式: evaluate(仅评测) 或 evaluate_optimize(评测+优化)，默认evaluate"},
            "max_samples": {"type": "integer", "description": "最大评测样本数(可选)"},
        },
        "required": ["model_ids", "generation_prompt_ids", "evaluation_prompt_ids", "judge_model_id"],
    },
)
async def run_domain_evaluation(db: AsyncSession, user: models.User, **kwargs):
    model_ids = kwargs["model_ids"]
    for mid in model_ids:
        result = await db.execute(
            select(models.ModelConfig).where(
                models.ModelConfig.id == mid, models.ModelConfig.user_id == user.id
            )
        )
        if not result.scalar_one_or_none():
            return {"error": f"模型 ID {mid} 不存在或无权限"}

    domain = kwargs.get("domain", "general")
    evaluator_config = {
        "performance": True,
        "domain_eval": True,
        "domain": domain,
        "generation_prompt_ids": kwargs["generation_prompt_ids"],
        "evaluation_prompt_ids": kwargs["evaluation_prompt_ids"],
        "judge_model_id": kwargs["judge_model_id"],
        "eval_mode": kwargs.get("eval_mode", "evaluate"),
    }
    if kwargs.get("max_samples"):
        evaluator_config["max_samples"] = kwargs["max_samples"]

    domain_names = {"medical": "医疗", "finance": "金融", "industrial": "工业", "legal": "法律", "education": "教育", "general": "通用"}
    task = models.EvaluationTask(
        user_id=user.id,
        name=f"{domain_names.get(domain, domain)}领域评测",
        description=f"使用双Prompt模式进行{domain_names.get(domain, domain)}领域垂直评测",
        model_ids=model_ids,
        dataset_id=kwargs.get("dataset_id"),
        evaluator_config=evaluator_config,
        status="pending",
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)

    # Commit BEFORE dispatching Celery to avoid race condition
    await db.commit()

    from app.services.evaluation import run_evaluation_task
    celery_result = run_evaluation_task.delay(task.id)
    task.celery_task_id = celery_result.id
    await db.flush()

    return {
        "id": task.id,
        "name": task.name,
        "domain": domain,
        "status": task.status,
        "message": f"{domain_names.get(domain, domain)}领域评测任务已创建 (ID: {task.id})，使用双Prompt模式评测",
        "navigate": f"/evaluations/{task.id}",
    }


@registry.register(
    name="diagnose_evaluation",
    description="对评测结果中的低分样本进行详细诊断。使用上位评判模型分析扣分原因、问题片段和改进建议。",
    category="domain_eval",
    parameters={
        "type": "object",
        "properties": {
            "task_id": {"type": "integer", "description": "评测任务ID"},
            "score_threshold": {"type": "number", "description": "低分阈值(0-1)，低于此分数的样本会被诊断，默认0.6"},
        },
        "required": ["task_id"],
    },
)
async def diagnose_evaluation(db: AsyncSession, user: models.User, **kwargs):
    from app.core.http import make_async_httpx_client
    task_id = kwargs["task_id"]
    threshold = kwargs.get("score_threshold", 0.6)

    task_result = await db.execute(
        select(models.EvaluationTask).where(
            models.EvaluationTask.id == task_id, models.EvaluationTask.user_id == user.id
        )
    )
    task = task_result.scalar_one_or_none()
    if not task:
        return {"error": "评测任务不存在"}
    if task.status != "completed":
        return {"error": f"评测任务尚未完成 (当前状态: {task.status})"}

    # Get low-scoring results
    results_q = await db.execute(
        select(models.EvaluationResult).where(models.EvaluationResult.task_id == task_id)
    )
    all_results = results_q.scalars().all()
    low_results = [r for r in all_results if r.scores.get("domain_overall", 1.0) < threshold]

    if not low_results:
        return {"message": "没有发现低分样本", "count": 0}

    config = task.evaluator_config
    judge_model_id = config.get("judge_model_id")
    if not judge_model_id:
        return {"error": "未配置评判模型"}

    from app.core.security import decrypt_api_key
    judge_mc = await db.execute(select(models.ModelConfig).where(models.ModelConfig.id == judge_model_id))
    judge_model = judge_mc.scalar_one_or_none()
    if not judge_model:
        return {"error": "评判模型不存在"}

    api_key = decrypt_api_key(judge_model.api_key_encrypted) if judge_model.api_key_encrypted else None
    base_url = judge_model.base_url or "https://api.openai.com/v1"
    url = f"{base_url}/chat/completions"
    diagnosed = 0

    for r in low_results[:20]:  # Limit to 20 samples
        prompt = f"""你是一个专业的AI评测诊断专家。请详细分析以下模型回答的问题。

## 原始输入
{r.input_text or ''}

## 模型回答
{r.output_text or ''}

## 当前评分
{json.dumps(r.scores, ensure_ascii=False)}

请以JSON格式输出诊断结果：
{{"problems": [{{"segment": "有问题的原文片段", "issue": "问题描述", "suggestion": "改进建议"}}], "reasoning": "整体诊断说明", "severity": "high/medium/low"}}

请直接输出JSON。"""

        try:
            async with make_async_httpx_client(timeout=60.0) as client:
                resp = await client.post(url, headers={
                    "Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
                }, json={"model": judge_model.model_name, "messages": [{"role": "user", "content": prompt}], "max_tokens": 1024})
            if resp.status_code == 200:
                import re
                raw = resp.json()["choices"][0]["message"]["content"]
                text = raw.strip()
                if text.startswith("```"):
                    text = re.sub(r"^```(?:json)?\s*", "", text)
                    text = re.sub(r"\s*```$", "", text)
                try:
                    diagnosis = json.loads(text)
                except json.JSONDecodeError:
                    match = re.search(r"\{[\s\S]*\}", text)
                    diagnosis = json.loads(match.group()) if match else {"reasoning": text}
                meta = dict(r.result_metadata) if r.result_metadata else {}
                meta["diagnosis"] = diagnosis
                meta["problems"] = diagnosis.get("problems", meta.get("problems", []))
                r.result_metadata = meta
                diagnosed += 1
            else:
                import logging
                logging.getLogger(__name__).warning(f"Diagnose API returned HTTP {resp.status_code} for result {r.id}")
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to diagnose result {r.id}: {e}")

    await db.flush()
    return {
        "message": f"已诊断 {diagnosed} 个低分样本 (阈值: {threshold})",
        "diagnosed_count": diagnosed,
        "total_low": len(low_results),
        "navigate": f"/results/{task_id}",
    }


@registry.register(
    name="generate_training_data",
    description="基于诊断结果，使用上位评判模型为低分样本生成修正版高质量训练数据。",
    category="domain_eval",
    parameters={
        "type": "object",
        "properties": {
            "task_id": {"type": "integer", "description": "评测任务ID"},
        },
        "required": ["task_id"],
    },
)
async def generate_training_data(db: AsyncSession, user: models.User, **kwargs):
    from app.core.http import make_async_httpx_client
    task_id = kwargs["task_id"]

    task_result = await db.execute(
        select(models.EvaluationTask).where(
            models.EvaluationTask.id == task_id, models.EvaluationTask.user_id == user.id
        )
    )
    task = task_result.scalar_one_or_none()
    if not task:
        return {"error": "评测任务不存在"}

    config = task.evaluator_config
    judge_model_id = config.get("judge_model_id")
    if not judge_model_id:
        return {"error": "未配置评判模型"}

    from app.core.security import decrypt_api_key
    judge_mc = await db.execute(select(models.ModelConfig).where(models.ModelConfig.id == judge_model_id))
    judge_model = judge_mc.scalar_one_or_none()
    if not judge_model:
        return {"error": "评判模型不存在"}

    api_key = decrypt_api_key(judge_model.api_key_encrypted) if judge_model.api_key_encrypted else None
    base_url = judge_model.base_url or "https://api.openai.com/v1"
    url = f"{base_url}/chat/completions"

    results_q = await db.execute(
        select(models.EvaluationResult).where(models.EvaluationResult.task_id == task_id)
    )
    all_results = results_q.scalars().all()
    low_results = [r for r in all_results if r.scores.get("domain_overall", 1.0) < 0.6 or (r.result_metadata and r.result_metadata.get("diagnosis"))]

    generated = 0
    for r in low_results[:20]:
        diagnosis = (r.result_metadata or {}).get("diagnosis", {})
        problems_desc = json.dumps(diagnosis.get("problems", []), ensure_ascii=False)

        gen_prompt = f"""你是一个专业的AI训练数据优化专家。请基于以下诊断结果，生成一个高质量的修正版回答。

## 原始输入
{r.input_text or ''}

## 原始回答
{r.output_text or ''}

## 诊断问题
{problems_desc}

## 诊断说明
{diagnosis.get('reasoning', '无')}

请直接生成修正后的高质量回答，只输出修正后的回答内容。"""

        try:
            async with make_async_httpx_client(timeout=60.0) as client:
                resp = await client.post(url, headers={
                    "Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
                }, json={"model": judge_model.model_name, "messages": [{"role": "user", "content": gen_prompt}], "max_tokens": 2048})
            if resp.status_code == 200:
                corrected = resp.json()["choices"][0]["message"]["content"]
                gtd = models.GeneratedTrainingData(
                    task_id=task_id, result_id=r.id, user_id=user.id,
                    original_input=r.input_text, original_output=r.output_text,
                    corrected_output=corrected, diagnosis=diagnosis,
                    improvement_notes=diagnosis.get("reasoning", ""),
                )
                db.add(gtd)
                generated += 1
            else:
                import logging
                logging.getLogger(__name__).warning(f"Generate API returned HTTP {resp.status_code} for result {r.id}")
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to generate training data for result {r.id}: {e}")

    await db.flush()
    return {
        "message": f"已为 {generated} 个低分样本生成修正版训练数据",
        "generated_count": generated,
        "navigate": f"/evaluations/{task_id}/optimize",
    }


@registry.register(
    name="export_optimized_dataset",
    description="将审核通过的优化训练数据导出为新的JSONL数据集，可用于模型再微调。",
    category="domain_eval",
    parameters={
        "type": "object",
        "properties": {
            "task_id": {"type": "integer", "description": "评测任务ID"},
            "name": {"type": "string", "description": "新数据集名称"},
        },
        "required": ["task_id", "name"],
    },
)
async def export_optimized_dataset(db: AsyncSession, user: models.User, **kwargs):
    task_id = kwargs["task_id"]
    name = kwargs["name"]

    # Only export approved data for quality control
    result = await db.execute(
        select(models.GeneratedTrainingData).where(
            models.GeneratedTrainingData.task_id == task_id,
            models.GeneratedTrainingData.user_id == user.id,
            models.GeneratedTrainingData.is_approved == True,
        )
    )
    items = result.scalars().all()
    if not items:
        # Check if there's unapproved data
        all_result = await db.execute(
            select(func.count(models.GeneratedTrainingData.id)).where(
                models.GeneratedTrainingData.task_id == task_id,
                models.GeneratedTrainingData.user_id == user.id,
            )
        )
        total = all_result.scalar() or 0
        if total > 0:
            return {"error": f"有 {total} 条优化数据尚未审核通过，请先在优化页面审核后再导出", "navigate": f"/evaluations/{task_id}/optimize"}
        return {"error": "没有可导出的优化数据，请先生成训练数据"}

    records = []
    for item in items:
        records.append({
            "input": item.original_input or "",
            "output": item.corrected_output or "",
            "original_output": item.original_output or "",
            "improvement_notes": item.improvement_notes or "",
        })

    jsonl_content = "\n".join(json.dumps(r, ensure_ascii=False) for r in records)
    content_bytes = jsonl_content.encode("utf-8")

    from app.services.storage import StorageService
    import asyncio
    storage = StorageService()
    file_path = f"datasets/{user.id}/generated_{task_id}_{name}.jsonl"
    await storage.upload_bytes(file_path, content_bytes, "application/jsonl")

    dataset = models.Dataset(
        user_id=user.id, name=name,
        description=f"从评测任务 #{task_id} 优化导出的训练数据",
        category="training", format="jsonl",
        size=len(records), file_path=file_path,
        schema_meta={"fields": ["input", "output", "original_output", "improvement_notes"]},
        status="ready",
    )
    db.add(dataset)
    await db.flush()
    await db.refresh(dataset)
    return {
        "id": dataset.id,
        "name": dataset.name,
        "size": dataset.size,
        "message": f"数据集 '{name}' 已导出 ({len(records)} 条记录)",
        "navigate": "/datasets",
    }
