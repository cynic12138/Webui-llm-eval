/** Shared metric metadata, helpers, and formatting for all evaluation pages */

/** Metric display name + description for all known score keys */
export const METRIC_INFO: Record<string, { name: string; desc: string }> = {
  // LLM-as-Judge
  judge_accuracy: { name: "准确性 (Judge)", desc: "裁判模型评估回答的事实准确性，1-10分归一化" },
  judge_fluency: { name: "流畅性 (Judge)", desc: "裁判模型评估语言表达的流畅自然程度" },
  judge_relevance: { name: "相关性 (Judge)", desc: "裁判模型评估回答与问题的相关程度" },
  // Hallucination
  hallucination_consistency: { name: "幻觉一致性", desc: "同一问题多次采样，回答间的一致性。越高表示越不容易产生幻觉" },
  hallucination_risk: { name: "幻觉风险", desc: "模型产生幻觉的风险程度，= 1 - 一致性分数" },
  // Robustness
  robustness_score: { name: "鲁棒性", desc: "对输入进行拼写错误/同义替换/大小写变换后，输出的稳定程度" },
  // Consistency
  consistency_score: { name: "一致性", desc: "多次采样输出的自洽程度，衡量模型回答是否稳定可靠" },
  // Safety
  toxicity: { name: "无毒性", desc: "回复中不含毒性/攻击性内容的程度 (1=完全无毒)" },
  severe_toxicity: { name: "无严重毒性", desc: "回复中不含严重毒性内容的程度" },
  obscene: { name: "无低俗", desc: "回复中不含低俗/淫秽内容的程度" },
  insult: { name: "无侮辱", desc: "回复中不含侮辱性语言的程度" },
  threat: { name: "无威胁", desc: "回复中不含威胁性内容的程度" },
  identity_attack: { name: "无身份攻击", desc: "回复中不含针对特定群体的攻击" },
  bias_score: { name: "无偏见", desc: "回复中不含性别/种族/宗教偏见的程度" },
  safety_overall: { name: "安全总分", desc: "所有安全维度的综合得分" },
  safety_keyword_based: { name: "安全 (关键词)", desc: "基于关键词匹配的安全性评估" },
  // RAG
  rag_faithfulness: { name: "RAG 忠实性", desc: "回答是否忠实于提供的上下文，不编造上下文中没有的信息" },
  rag_relevance: { name: "RAG 相关性", desc: "回答与用户问题的相关程度" },
  rag_completeness: { name: "RAG 完整性", desc: "回答是否涵盖了足够的信息量" },
  // Benchmarks
  mmlu_accuracy: { name: "MMLU-Pro", desc: "大规模多任务语言理解测试，覆盖数十个学科领域的选择题准确率" },
  gsm8k_accuracy: { name: "GSM8K", desc: "小学数学推理题，测试多步数学推理能力" },
  "humaneval_pass@1": { name: "HumanEval", desc: "代码生成基准，测试根据函数签名生成正确代码的能力" },
  ceval_accuracy: { name: "C-Eval", desc: "中文综合能力评测，覆盖人文、理工、社科等52个学科" },
  hellaswag_accuracy: { name: "HellaSwag", desc: "常识推理测试，选择最合理的句子续写" },
  truthfulqa_accuracy: { name: "TruthfulQA", desc: "真实性问答测试，评估模型是否会给出常见错误答案" },
  math_accuracy: { name: "MATH", desc: "数学竞赛题，测试高级数学推理和解题能力" },
  arc_accuracy: { name: "ARC", desc: "AI2 推理挑战，小学科学考试选择题" },
  ifeval_strict: { name: "IFEval", desc: "指令遵循评测，检查模型是否严格遵守格式/长度/内容约束" },
  "bigcodebench_pass@1": { name: "BigCodeBench", desc: "大规模代码生成基准，测试复杂编程任务的完成能力" },
  mt_bench_score: { name: "MT-Bench", desc: "多轮对话质量评测，测试模型在连续对话中的表现" },
  mt_bench_helpfulness: { name: "MT有用性", desc: "回复的实用价值 (裁判模型子维度)" },
  mt_bench_relevance: { name: "MT相关性", desc: "回复与问题的关联度和上下文利用" },
  mt_bench_coherence: { name: "MT连贯性", desc: "逻辑一致性和结构清晰度" },
  mt_bench_depth: { name: "MT深度", desc: "分析和解释的深入程度" },
  mt_bench_instruction_following: { name: "MT指令遵循", desc: "对用户指令的精确执行" },
  alpaca_quality: { name: "AlpacaEval", desc: "指令遵循质量评测，测试开放式指令的回答质量" },
  alpaca_accuracy: { name: "Alpaca准确性", desc: "内容的事实正确性 (裁判模型子维度)" },
  alpaca_helpfulness: { name: "Alpaca有用性", desc: "回复的实用价值" },
  alpaca_clarity: { name: "Alpaca清晰度", desc: "表达清晰度和组织结构" },
  alpaca_completeness: { name: "Alpaca完整性", desc: "对指令各方面的覆盖程度" },
  alpaca_conciseness: { name: "Alpaca简洁性", desc: "表达的精炼程度" },
  swe_resolve_rate: { name: "SWE-Bench", desc: "软件工程基准，测试根据 Issue 描述生成代码修复的能力" },
  swe_correctness: { name: "SWE正确性", desc: "修复方案的正确程度 (裁判模型子维度)" },
  swe_code_quality: { name: "SWE代码质量", desc: "代码的规范性和可读性" },
  swe_completeness: { name: "SWE完整性", desc: "对边界情况和相关修改的覆盖" },
  swe_explanation: { name: "SWE解释质量", desc: "修复思路和决策的说明" },
  // HealthBench
  healthbench_score: { name: "HealthBench 总分", desc: "医疗健康场景综合评分，基于医学专家编写的 rubric 标准逐条评判" },
  healthbench_hard_score: { name: "HealthBench-Hard", desc: "高难度医疗场景的共识标准通过率" },
  healthbench_accuracy: { name: "医学准确性", desc: "医学事实是否正确，是否存在危险/误导性建议" },
  healthbench_completeness: { name: "医学完整性", desc: "回答是否涵盖所有关键医学信息和建议" },
  healthbench_context_awareness: { name: "上下文感知", desc: "是否根据患者情况、地理位置、可用资源等调整建议" },
  healthbench_communication_quality: { name: "沟通质量", desc: "语言是否适合目标受众（专业术语 vs 通俗解释）" },
  healthbench_instruction_following: { name: "指令遵循 (HB)", desc: "是否按用户要求的格式和详细程度作答" },
  // Domain
  domain_overall: { name: "领域总分", desc: "垂直领域评测综合得分，由裁判模型按自定义评测标准打分" },
  domain_accuracy: { name: "领域准确性", desc: "在特定领域中回答的事实准确程度" },
  domain_completeness: { name: "领域完整性", desc: "在特定领域中回答是否涵盖关键要点" },
  domain_professionalism: { name: "领域专业性", desc: "回答的专业术语使用和深度是否到位" },
  domain_safety: { name: "领域安全性", desc: "回答在该领域中是否存在安全风险" },
  // Chain-of-Thought
  cot_step_count: { name: "推理步数", desc: "模型输出中包含的推理步骤数量（非0-1归一化）" },
  cot_has_reasoning: { name: "包含推理", desc: "输出中是否包含step-by-step推理过程 (0或1)" },
  cot_answer_correct: { name: "答案正确", desc: "经过推理后最终答案是否与参考答案一致 (0或1)" },
  // Multi-turn
  multiturn_coherence: { name: "多轮连贯性", desc: "在多轮对话中上下文理解和回复连贯性" },
  // Tool Calling
  tool_selection_accuracy: { name: "工具选择准确率", desc: "模型是否正确选择了应该调用的工具/函数" },
  argument_accuracy: { name: "参数准确率", desc: "工具调用的参数是否正确" },
  // Long Context
  needle_retrieval: { name: "长文本检索", desc: "在长上下文中检索特定信息的能力 (大海捞针测试)" },
  // Structured Output
  json_valid: { name: "JSON 有效性", desc: "输出是否为有效的 JSON 格式" },
  schema_compliant: { name: "Schema 符合度", desc: "JSON 输出是否符合指定的 Schema 结构" },
  // Multimodal
  vision_accuracy: { name: "视觉理解", desc: "多模态图像理解和描述的准确性" },
  text_accuracy: { name: "文本准确率", desc: "纯文本模式下的回答准确率" },
  // Cost
  cost_usd: { name: "成本 (USD)", desc: "单次调用的估算成本（非0-1归一化）" },
  score_per_dollar: { name: "性价比", desc: "每美元获得的分数，衡量成本效益" },
  // Multilingual
  multilingual_avg: { name: "多语言平均", desc: "跨语言能力的平均得分" },
  // Objective Metrics
  rouge_1: { name: "ROUGE-1", desc: "基于 unigram 的文本重叠率，衡量与参考答案的相似度" },
  rouge_2: { name: "ROUGE-2", desc: "基于 bigram 的文本重叠率，关注连续词组匹配" },
  rouge_l: { name: "ROUGE-L", desc: "基于最长公共子序列的文本相似度" },
  bleu: { name: "BLEU", desc: "机器翻译评估指标，衡量生成文本与参考文本的 n-gram 精确率" },
  meteor: { name: "METEOR", desc: "综合考虑精确率、召回率和词序的文本相似度指标" },
  exact_match: { name: "精确匹配", desc: "生成文本与参考文本是否完全一致 (0或1)" },
  token_f1: { name: "Token F1", desc: "基于 token 级别的精确率和召回率的调和平均" },
  embedding_cosine: { name: "语义相似度", desc: "基于 Embedding 的余弦相似度，衡量语义层面的相似程度" },
  bertscore_f1: { name: "BERTScore", desc: "基于 BERT 嵌入的语义相似度，更好地捕捉释义和同义表达" },
  distinct_1: { name: "Distinct-1", desc: "不同 unigram 占总词数的比例，衡量词汇多样性" },
  distinct_2: { name: "Distinct-2", desc: "不同 bigram 占总 bigram 的比例，衡量表达多样性" },
  response_length: { name: "回复长度", desc: "模型回复的字符数（原始值，非0-1归一化）" },
  entity_match_f1: { name: "实体匹配 F1", desc: "生成文本与参考文本中命名实体的匹配程度" },
  // Code Execution
  "code_pass@1": { name: "代码通过率", desc: "代码执行后通过所有测试用例的比率" },
  // Additional evaluator scores
  keyword_score: { name: "关键词得分", desc: "输出中包含关键信息/关键词的比率" },
  quality_score: { name: "质量得分", desc: "综合质量评分 (用于性价比分析)" },
  avg_quality_score: { name: "平均质量得分", desc: "所有样本的平均质量评分" },
};

/** Raw (non-normalized) metrics -- these need special formatting */
export const RAW_METRICS = new Set(["response_length", "cot_step_count", "cost_usd"]);

/** Get display name for a metric key */
export function getMetricName(key: string): string {
  if (METRIC_INFO[key]) return METRIC_INFO[key].name;
  // Handle dynamic keys
  if (key.startsWith("healthbench_theme_")) return `HB主题: ${key.replace("healthbench_theme_", "")}`;
  if (key.startsWith("healthbench_")) return `HB: ${key.replace("healthbench_", "")}`;
  if (key.startsWith("domain_")) return `领域: ${key.replace("domain_", "")}`;
  if (key.startsWith("judge_")) return `Judge: ${key.replace("judge_", "")}`;
  if (key.startsWith("multilingual_")) return `多语言: ${key.replace("multilingual_", "")}`;
  if (key.startsWith("livebench_")) return `LiveBench: ${key.replace("livebench_", "")}`;
  return key;
}

/** Get description for a metric key */
export function getMetricDesc(key: string): string {
  if (METRIC_INFO[key]) return METRIC_INFO[key].desc;
  if (key.startsWith("healthbench_theme_")) return "HealthBench 特定医疗主题的子维度评分";
  if (key.startsWith("domain_")) return "垂直领域评测的子维度评分";
  if (key.startsWith("judge_")) return "裁判模型评估的子维度评分 (1-10分归一化到0-1)";
  if (key.startsWith("multilingual_")) return "该语言的翻译/回答质量评分";
  if (key.startsWith("livebench_")) return "LiveBench 该类别的评测准确率";
  return "评测指标";
}

/** Format a score value for display: raw metrics show as integer with unit, others as percentage */
export function formatScore(key: string, val: number): string {
  if (key === "response_length") return `${Math.round(val).toLocaleString()} 字符`;
  if (key === "cot_step_count") return `${Math.round(val)} 步`;
  if (key === "cost_usd") return `$${val.toFixed(4)}`;
  return `${(val * 100).toFixed(0)}%`;
}

/** Get tag color for a score value */
export function scoreTagColor(key: string, val: number): string {
  if (RAW_METRICS.has(key)) return "blue";
  return val > 0.7 ? "success" : val > 0.4 ? "warning" : "error";
}
