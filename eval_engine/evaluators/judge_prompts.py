"""
LLM-as-a-Judge evaluation prompts for all benchmark evaluators.

Each benchmark has:
  1. Evaluation criteria (dimensions + rubric)
  2. Structured prompt template with role, task, scoring rules, examples
  3. Expected JSON output format
  4. Post-processing helpers

Following the 6-step methodology:
  1. Define evaluation criteria
  2. Design evaluation prompts
  3. Prepare input content
  4. Execute model judgment
  5. Post-process parsing
  6. Validation & calibration
"""

# ═══════════════════════════════════════════════════════════════════════
# HealthBench (main) — Per-Criterion Binary Grading
# ═══════════════════════════════════════════════════════════════════════
#
# Official methodology: grade each rubric criterion independently.
# Score = sum(points for met criteria) / max_positive_points, clipped [0,1]
#
# Data format (healthbench.jsonl, 5000 samples):
#   rubrics: [{criterion: str, points: int(-10~+10), tags: [str]}]
#   tags: "axis:accuracy|completeness|context_awareness|communication_quality|instruction_following"
#         "level:example|cluster"
#
# 5 axes: accuracy(33%), completeness(39%), context_awareness(16%),
#          communication_quality(8%), instruction_following(4%)
# 7 themes: emergency_referrals, context_seeking, global_health,
#           health_data_tasks, expertise_tailored_communication,
#           responding_under_uncertainty, response_depth

HEALTHBENCH_CRITERION_JUDGE_SYSTEM = """You are a physician-level medical evaluation judge. You grade whether an AI medical assistant's response meets a specific rubric criterion written by expert physicians.

Core principles:
- Apply strict medical standards — accuracy must align with current evidence-based guidelines
- A criterion with multiple requirements must have ALL of them met to return true
- Phrases like "such as" or "for example" are non-exhaustive: the response does not need to mention every listed example, only demonstrate the described behavior
- For NEGATIVE criteria (describing harmful/undesirable behavior): return true if the bad behavior IS PRESENT in the response
- Consider the FULL conversation context, not just the last message
- Be objective and consistent"""

HEALTHBENCH_CRITERION_JUDGE_TEMPLATE = """You are evaluating an AI medical assistant's response against a specific physician-written rubric criterion.

## Conversation
{conversation}

## AI Assistant's Response
{response}

## Rubric Criterion to Evaluate
{criterion}

## Point Value: {points}
{point_explanation}

## Instructions
1. Carefully read the conversation context and the assistant's response.
2. Determine whether the response meets the criterion described above.
3. IMPORTANT: If the criterion contains multiple requirements (connected by "and", commas, or semicolons), ALL must be satisfied for criteria_met to be true.
4. IMPORTANT: If the criterion describes UNDESIRABLE behavior (typically has negative points), return criteria_met=true if the response EXHIBITS that bad behavior.
5. Exception: Phrases like "such as", "for example", "e.g." are illustrative — the response need not include every example listed, only demonstrate the general behavior described.

Respond with ONLY a JSON object:
```json
{{"explanation": "Brief reasoning about whether the criterion is met...", "criteria_met": true/false}}
```"""


# ═══════════════════════════════════════════════════════════════════════
# HealthBench-Hard (Consensus) — Holistic Criteria Grading
# ═══════════════════════════════════════════════════════════════════════
#
# Data format (healthbench_hard.jsonl, 29511 samples):
#   rubrics: [{criteria: str, category: str}]  ← note: "criteria" not "criterion"!
#   No points or tags fields.
#   34 cluster categories covering 7 theme dimensions.
#   Each sample has exactly 1 holistic criteria string with multiple bullet points.
#
# The criteria text itself is the complete evaluation rubric — it describes
# what to check in a step-by-step or bullet-point format.

HEALTHBENCH_HARD_JUDGE_SYSTEM = """You are a physician-level medical evaluation judge. You evaluate AI medical assistant responses using consensus criteria agreed upon by multiple physicians.

Core principles:
- Apply strict medical standards aligned with current evidence-based guidelines
- Evaluate the response holistically against ALL requirements in the criteria
- If ANY requirement in the criteria is not met, the overall criteria is NOT met
- Be especially rigorous: these are consensus criteria that physicians agree are essential
- Consider the FULL conversation context"""

HEALTHBENCH_HARD_JUDGE_TEMPLATE = """You are evaluating an AI medical assistant's response against a physician consensus criterion.

## Conversation
{conversation}

## AI Assistant's Response
{response}

## Evaluation Criteria
{criteria}

## Category
{category}

## Instructions
1. Carefully read the conversation and the assistant's response.
2. Evaluate the response against EVERY requirement stated in the criteria above.
3. The criteria may contain multiple conditions, steps, or bullet points — ALL must be satisfied.
4. If the criteria describes a step-by-step evaluation process, follow each step in order.
5. If ANY step or condition fails, the overall criteria is NOT met.

Respond with ONLY a JSON object:
```json
{{"explanation": "Step-by-step evaluation against each requirement in the criteria...", "criteria_met": true/false}}
```"""


# ═══════════════════════════════════════════════════════════════════════
# MT-Bench — Multi-turn Dialogue Quality
# ═══════════════════════════════════════════════════════════════════════
# Dimensions: helpfulness, relevance, coherence, depth, instruction_following

MT_BENCH_JUDGE_SYSTEM = """You are an expert dialogue quality evaluator. You assess multi-turn conversations between a user and an AI assistant with focus on conversational competence, factual accuracy, and response quality across turns."""

MT_BENCH_JUDGE_TEMPLATE = """## Task
Evaluate the quality of a multi-turn AI assistant dialogue. Score each dimension on a 0-10 scale.

## Dialogue

### Turn 1
**User**: {turn1_user}
**Assistant**: {turn1_assistant}

### Turn 2
**User**: {turn2_user}
**Assistant**: {turn2_assistant}

## Scoring Dimensions

### 1. Helpfulness (mt_bench_helpfulness)
Does the response provide useful, actionable information?
- **10**: Exceptionally helpful — goes beyond the question with valuable insights, practical examples, and actionable advice.
- **8-9**: Very helpful — thoroughly addresses the question with useful details.
- **6-7**: Moderately helpful — addresses the main point but could be more thorough.
- **4-5**: Somewhat helpful — provides basic information but misses important aspects.
- **2-3**: Minimally helpful — vague or too superficial to be useful.
- **0-1**: Not helpful — irrelevant, incorrect, or empty response.

### 2. Relevance (mt_bench_relevance)
Does each turn properly address what was asked? Does Turn 2 build on Turn 1?
- **10**: Both turns are perfectly on-topic. Turn 2 seamlessly builds on the context from Turn 1.
- **8-9**: Highly relevant with strong turn-to-turn coherence.
- **6-7**: Mostly relevant but Turn 2 may not fully leverage Turn 1 context.
- **4-5**: Partially relevant — some drift from the topic or poor context utilization.
- **2-3**: Significant relevance issues — ignores key aspects or the turn-to-turn connection.
- **0-1**: Completely off-topic or ignores the conversation flow.

### 3. Coherence (mt_bench_coherence)
Is the overall dialogue logically consistent and well-structured?
- **10**: Perfectly coherent — logical flow, no contradictions, well-organized arguments.
- **8-9**: Very coherent with clear structure and consistent reasoning.
- **6-7**: Generally coherent but with minor logical gaps or structural issues.
- **4-5**: Some coherence issues — contradictions, unclear reasoning, or poor organization.
- **2-3**: Significant coherence problems — contradicts itself or is disorganized.
- **0-1**: Incoherent — confusing, contradictory, or incomprehensible.

### 4. Depth (mt_bench_depth)
Does the response provide sufficient analytical depth and detail?
- **10**: Deep, insightful analysis with nuanced understanding. Provides multiple perspectives, examples, and thorough explanation.
- **8-9**: Good depth with meaningful analysis and supporting details.
- **6-7**: Adequate depth — covers the topic but could explore further.
- **4-5**: Shallow — provides surface-level information without analysis.
- **2-3**: Very shallow — barely addresses the topic.
- **0-1**: No meaningful depth — trivial or empty response.

### 5. Instruction Following (mt_bench_instruction_following)
Does the assistant follow the user's instructions precisely?
- **10**: Perfectly follows all explicit and implicit instructions in both turns.
- **8-9**: Follows instructions well with minor deviations.
- **6-7**: Mostly follows instructions but misses some aspects.
- **4-5**: Partially follows instructions — notable gaps.
- **2-3**: Largely ignores specific instructions.
- **0-1**: Completely fails to follow instructions.

## Scoring Examples

### Example: Energy sources discussion
Turn 1: "What are the main differences between renewable and non-renewable energy?"
Turn 2: "Can you elaborate on the environmental impact of each?"

- Good response: Turn 1 clearly distinguishes types with examples. Turn 2 deepens with specific environmental data, references Turn 1 context.
  → helpfulness: 9, relevance: 9, coherence: 9, depth: 8, instruction_following: 9
- Poor response: Turn 1 gives a one-sentence answer. Turn 2 repeats Turn 1 content without elaboration.
  → helpfulness: 3, relevance: 5, coherence: 4, depth: 2, instruction_following: 4

## Output Format
You MUST respond with ONLY a valid JSON object:
```json
{{
  "reasoning": "Analysis of dialogue quality across turns...",
  "scores": {{
    "mt_bench_helpfulness": <0-10>,
    "mt_bench_relevance": <0-10>,
    "mt_bench_coherence": <0-10>,
    "mt_bench_depth": <0-10>,
    "mt_bench_instruction_following": <0-10>
  }}
}}
```"""


# ═══════════════════════════════════════════════════════════════════════
# AlpacaEval — Instruction-Following Quality
# ═══════════════════════════════════════════════════════════════════════
# Dimensions: accuracy, helpfulness, clarity, completeness, conciseness

ALPACA_EVAL_JUDGE_SYSTEM = """You are an expert evaluator for AI instruction-following capability. You assess how well an AI assistant responds to user instructions across multiple quality dimensions."""

ALPACA_EVAL_JUDGE_TEMPLATE = """## Task
Evaluate the AI assistant's response to the given instruction. Score each dimension on a 0-10 scale.

## Instruction
{instruction}

{reference_section}

## AI Response
{response}

## Scoring Dimensions

### 1. Accuracy (alpaca_accuracy)
Is the content factually correct and reliable?
- **10**: All statements are factually correct and verifiable. Demonstrates deep, accurate knowledge.
- **8-9**: Highly accurate with negligible errors that don't affect utility.
- **6-7**: Mostly accurate but contains minor factual imprecisions.
- **4-5**: Contains noticeable factual errors that could mislead.
- **2-3**: Significant factual errors throughout.
- **0-1**: Predominantly incorrect or fabricated information.

### 2. Helpfulness (alpaca_helpfulness)
Does the response effectively serve the user's needs?
- **10**: Exceptionally useful — directly addresses the instruction with practical, actionable content and added value.
- **8-9**: Very helpful — thoroughly addresses the instruction with useful details.
- **6-7**: Moderately helpful — addresses the main point adequately.
- **4-5**: Somewhat helpful — provides basic information but misses key aspects.
- **2-3**: Barely helpful — too vague or tangential.
- **0-1**: Not helpful — irrelevant or counterproductive.

### 3. Clarity (alpaca_clarity)
Is the response clear, well-organized, and easy to understand?
- **10**: Crystal clear — excellent structure, logical flow, appropriate formatting (lists, headers, etc.).
- **8-9**: Very clear with good organization.
- **6-7**: Generally clear but could be better organized.
- **4-5**: Somewhat unclear — confusing structure or poor flow.
- **2-3**: Difficult to understand or follow.
- **0-1**: Incomprehensible.

### 4. Completeness (alpaca_completeness)
Does the response fully address all aspects of the instruction?
- **10**: Comprehensively addresses every aspect of the instruction with appropriate depth.
- **8-9**: Addresses most aspects thoroughly with minor omissions.
- **6-7**: Covers the main topic but misses some relevant aspects.
- **4-5**: Partially complete — addresses only part of the instruction.
- **2-3**: Largely incomplete — misses most aspects.
- **0-1**: Does not address the instruction at all.

### 5. Conciseness (alpaca_conciseness)
Is the response appropriately concise without unnecessary padding?
- **10**: Perfect length — every sentence adds value, no filler or redundancy.
- **8-9**: Mostly concise with minimal unnecessary content.
- **6-7**: Acceptable length but contains some redundancy or filler.
- **4-5**: Noticeably padded or unnecessarily verbose.
- **2-3**: Excessively long with significant filler, or too short to be useful.
- **0-1**: Extremely verbose with almost no useful content, or empty.

## Scoring Examples

### Example: "Write a short poem about the ocean"
- Good response: A concise, evocative 4-8 line poem with ocean imagery, rhythm, and emotion.
  → accuracy: 8, helpfulness: 9, clarity: 9, completeness: 9, conciseness: 10
- Poor response: A 3-page essay about ocean geography with a poem buried in the middle.
  → accuracy: 7, helpfulness: 4, clarity: 5, completeness: 6, conciseness: 1

### Example: "Explain quantum computing to a 10-year-old"
- Good response: Uses a simple analogy (magic coin), avoids jargon, keeps it fun and accurate.
  → accuracy: 8, helpfulness: 9, clarity: 10, completeness: 7, conciseness: 9
- Poor response: Uses technical terms like "superposition" and "qubits" without explanation.
  → accuracy: 9, helpfulness: 3, clarity: 2, completeness: 5, conciseness: 6

## Output Format
You MUST respond with ONLY a valid JSON object:
```json
{{
  "reasoning": "Analysis of response quality across dimensions...",
  "scores": {{
    "alpaca_accuracy": <0-10>,
    "alpaca_helpfulness": <0-10>,
    "alpaca_clarity": <0-10>,
    "alpaca_completeness": <0-10>,
    "alpaca_conciseness": <0-10>
  }}
}}
```"""


# ═══════════════════════════════════════════════════════════════════════
# SWE-Bench — Software Engineering Problem Solving
# ═══════════════════════════════════════════════════════════════════════
# Dimensions: correctness, code_quality, completeness, explanation

SWE_BENCH_JUDGE_SYSTEM = """You are an expert software engineer and code reviewer. You evaluate proposed code fixes for software issues with focus on correctness, code quality, and engineering best practices."""

SWE_BENCH_JUDGE_TEMPLATE = """## Task
Evaluate a proposed code fix for a software engineering issue. Score each dimension on a 0-10 scale.

## Issue Description
{issue}

{test_section}

## Proposed Fix
```
{proposed_fix}
```

## Scoring Dimensions

### 1. Correctness (swe_correctness)
Does the fix actually solve the described issue?
- **10**: Fix is provably correct — addresses the root cause, handles all cases described in the issue, and would pass the associated tests.
- **8-9**: Highly likely to be correct — addresses the main issue with minor edge case concerns.
- **6-7**: Partially correct — fixes the main symptom but may not address root cause.
- **4-5**: Questionable correctness — approach is reasonable but has logical errors.
- **2-3**: Likely incorrect — fundamental misunderstanding of the issue.
- **0-1**: Completely wrong — doesn't address the issue or introduces new bugs.

### 2. Code Quality (swe_code_quality)
Is the code clean, idiomatic, and well-structured?
- **10**: Exemplary code — clean, idiomatic, well-named variables, proper error handling, follows project conventions.
- **8-9**: High-quality code with minor style issues.
- **6-7**: Acceptable quality — functional but could be cleaner.
- **4-5**: Below average — poor naming, missing error handling, or non-idiomatic patterns.
- **2-3**: Poor quality — hard to read, fragile, or anti-patterns.
- **0-1**: Unacceptable — incomprehensible or fundamentally flawed code structure.

### 3. Completeness (swe_completeness)
Does the fix handle all necessary cases and edge conditions?
- **10**: Complete fix — handles all described cases, edge conditions, and includes necessary related changes (imports, tests, docs).
- **8-9**: Nearly complete with minor missing edge cases.
- **6-7**: Addresses the main case but misses some edge conditions.
- **4-5**: Partial fix — only handles the happy path.
- **2-3**: Significantly incomplete — major cases unhandled.
- **0-1**: Trivially incomplete or no real fix provided.

### 4. Explanation (swe_explanation)
Does the response include clear reasoning about the fix?
- **10**: Excellent explanation — clearly identifies root cause, explains the fix strategy, justifies design decisions.
- **8-9**: Good explanation with clear reasoning.
- **6-7**: Basic explanation — describes what changed but not why.
- **4-5**: Minimal explanation — code only with brief comments.
- **2-3**: No meaningful explanation.
- **0-1**: No explanation or misleading explanation.

## Scoring Examples

### Example: "Fix off-by-one error in pagination"
- Good fix: Correctly adjusts index calculation, adds boundary check, includes test case, explains the off-by-one source.
  → correctness: 9, code_quality: 9, completeness: 9, explanation: 9
- Poor fix: Changes a `<` to `<=` without understanding the pagination logic, no explanation.
  → correctness: 4, code_quality: 5, completeness: 3, explanation: 1

## Output Format
You MUST respond with ONLY a valid JSON object:
```json
{{
  "reasoning": "Analysis of the proposed fix...",
  "scores": {{
    "swe_correctness": <0-10>,
    "swe_code_quality": <0-10>,
    "swe_completeness": <0-10>,
    "swe_explanation": <0-10>
  }}
}}
```"""


# ═══════════════════════════════════════════════════════════════════════
# Score key definitions (for frontend display)
# ═══════════════════════════════════════════════════════════════════════

BENCHMARK_SCORE_DEFINITIONS = {
    # HealthBench (per-axis scores computed from rubric grading)
    "healthbench_score": {"name": "HealthBench综合分", "description": "医学回复综合质量评分 (rubric加权)", "benchmark": "healthbench"},
    "healthbench_accuracy": {"name": "医学准确性", "description": "医学事实正确性 (axis:accuracy rubrics)", "benchmark": "healthbench"},
    "healthbench_completeness": {"name": "完整性", "description": "信息覆盖全面性 (axis:completeness rubrics)", "benchmark": "healthbench"},
    "healthbench_context_awareness": {"name": "情境感知", "description": "对患者背景和环境的适配 (axis:context_awareness rubrics)", "benchmark": "healthbench"},
    "healthbench_instruction_following": {"name": "指令遵循", "description": "对用户请求的响应准确度 (axis:instruction_following rubrics)", "benchmark": "healthbench"},
    "healthbench_communication_quality": {"name": "沟通质量", "description": "语言清晰度和受众适配性 (axis:communication_quality rubrics)", "benchmark": "healthbench"},
    # HealthBench-Hard (consensus binary grading)
    "healthbench_hard_score": {"name": "HealthBench-Hard综合分", "description": "共识标准通过率", "benchmark": "healthbench_hard"},
    # MT-Bench
    "mt_bench_score": {"name": "MT-Bench综合分", "description": "多轮对话综合质量评分", "benchmark": "mt_bench"},
    "mt_bench_helpfulness": {"name": "有用性", "description": "回复的实用价值", "benchmark": "mt_bench"},
    "mt_bench_relevance": {"name": "相关性", "description": "回复与问题的关联度和上下文利用", "benchmark": "mt_bench"},
    "mt_bench_coherence": {"name": "连贯性", "description": "逻辑一致性和结构清晰度", "benchmark": "mt_bench"},
    "mt_bench_depth": {"name": "深度", "description": "分析和解释的深入程度", "benchmark": "mt_bench"},
    "mt_bench_instruction_following": {"name": "指令遵循", "description": "对用户指令的精确执行", "benchmark": "mt_bench"},
    # AlpacaEval
    "alpaca_quality": {"name": "AlpacaEval综合分", "description": "指令遵循综合质量评分", "benchmark": "alpaca_eval"},
    "alpaca_accuracy": {"name": "准确性", "description": "内容的事实正确性", "benchmark": "alpaca_eval"},
    "alpaca_helpfulness": {"name": "有用性", "description": "回复的实用价值", "benchmark": "alpaca_eval"},
    "alpaca_clarity": {"name": "清晰度", "description": "表达清晰度和组织结构", "benchmark": "alpaca_eval"},
    "alpaca_completeness": {"name": "完整性", "description": "对指令各方面的覆盖程度", "benchmark": "alpaca_eval"},
    "alpaca_conciseness": {"name": "简洁性", "description": "表达的精炼程度", "benchmark": "alpaca_eval"},
    # SWE-Bench
    "swe_resolve_rate": {"name": "SWE-Bench综合分", "description": "代码修复综合质量评分", "benchmark": "swe_bench"},
    "swe_correctness": {"name": "正确性", "description": "修复方案的正确程度", "benchmark": "swe_bench"},
    "swe_code_quality": {"name": "代码质量", "description": "代码的规范性和可读性", "benchmark": "swe_bench"},
    "swe_completeness": {"name": "完整性", "description": "对边界情况和相关修改的覆盖", "benchmark": "swe_bench"},
    "swe_explanation": {"name": "解释质量", "description": "修复思路和决策的说明", "benchmark": "swe_bench"},
}
