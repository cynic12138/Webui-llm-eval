"""
Domain-specific evaluator using dual-prompt system:
  1. Generation prompt → tested model generates output
  2. Evaluation prompt → judge model scores the output

Returns structured scores, reasoning, and problem segments for highlighting.
"""
import json
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


JUDGE_SCORE_PROMPT = """你是一个专业的AI评测裁判。请严格按照以下评测标准对模型的回答进行打分。

## 原始输入
{input}

## 模型回答
{output}

## 评测要求
{eval_prompt}

## 输出格式要求
请以 JSON 格式输出，包含以下字段：
{{
  "overall": <0-1之间的总分>,
  "dimensions": {{
    "accuracy": <0-1 准确性>,
    "completeness": <0-1 完整性>,
    "professionalism": <0-1 专业性>,
    "safety": <0-1 安全性>
  }},
  "reasoning": "<扣分原因的详细说明>",
  "problems": [
    {{
      "segment": "<模型回答中有问题的原文片段>",
      "issue": "<问题描述>",
      "suggestion": "<改进建议>"
    }}
  ]
}}

请直接输出JSON，不要包含其他内容。"""


def _validate_score(value, field_name: str) -> float:
    """Validate and normalize a score to [0, 1] range."""
    try:
        score = float(value)
        if score < 0:
            logger.warning(f"Score '{field_name}' negative: {score}, clamping to 0")
            return 0.0
        # Handle models that return 0-10 or 0-100 scale
        if score > 1 and score <= 10:
            logger.info(f"Score '{field_name}' appears to be 0-10 scale ({score}), normalizing")
            return score / 10.0
        if score > 10:
            logger.info(f"Score '{field_name}' appears to be 0-100 scale ({score}), normalizing")
            return min(1.0, score / 100.0)
        return score
    except (ValueError, TypeError):
        logger.warning(f"Cannot parse score '{field_name}': {value}")
        return -1.0  # Sentinel value for parse failure


def parse_judge_scores(raw_output: str) -> dict:
    """Parse structured JSON from judge model output."""
    text = raw_output.strip()
    # Remove markdown code block markers (handle multiline)
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?\s*```\s*$", "", text)

    def _extract(data: dict) -> dict:
        overall = _validate_score(data.get("overall", -1), "overall")
        dimensions = {}
        for k, v in data.get("dimensions", {}).items():
            parsed = _validate_score(v, k)
            if parsed >= 0:
                dimensions[k] = parsed

        # If overall parse failed but dimensions exist, compute average
        if overall < 0 and dimensions:
            overall = sum(dimensions.values()) / len(dimensions)
            logger.info(f"Computed overall score from dimensions average: {overall:.3f}")
        elif overall < 0:
            overall = -1.0  # Keep sentinel to mark as unparseable

        return {
            "overall": overall,
            "dimensions": dimensions,
            "reasoning": data.get("reasoning", ""),
            "problems": data.get("problems", []),
        }

    def _try_parse(s: str) -> dict | None:
        try:
            data = json.loads(s)
            result = _extract(data)
            if result["overall"] >= 0:
                return result
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    # Attempt 1: direct parse
    result = _try_parse(text)
    if result:
        return result

    # Attempt 2: find JSON object in text (greedy)
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        result = _try_parse(match.group())
        if result:
            return result

    # Attempt 3: fix truncated JSON — find the scores part and close braces
    # This handles cases where "reasoning" field is too long and JSON is cut off
    score_match = re.search(
        r'"overall"\s*:\s*([\d.]+).*?"dimensions"\s*:\s*\{([^}]*)\}',
        text, re.DOTALL
    )
    if score_match:
        try:
            overall = float(score_match.group(1))
            dims_str = "{" + score_match.group(2) + "}"
            dimensions = json.loads(dims_str)
            overall_v = _validate_score(overall, "overall")
            dims = {}
            for k, v in dimensions.items():
                pv = _validate_score(v, k)
                if pv >= 0:
                    dims[k] = pv
            if overall_v >= 0:
                # Try to extract reasoning even if truncated
                reasoning_match = re.search(r'"reasoning"\s*:\s*"((?:[^"\\]|\\.)*)', text)
                reasoning = reasoning_match.group(1) if reasoning_match else ""
                return {
                    "overall": overall_v,
                    "dimensions": dims,
                    "reasoning": reasoning,
                    "problems": [],
                }
        except (ValueError, json.JSONDecodeError):
            pass

    # Final fallback — log warning clearly
    logger.warning(f"Failed to parse judge scores from output (len={len(raw_output)}): {raw_output[:300]}")
    return {
        "overall": 0.5,
        "dimensions": {},
        "reasoning": f"[解析失败] 评判模型输出无法解析为有效JSON，使用默认分数0.5。原始输出: {raw_output[:200]}",
        "problems": [],
        "_parse_failed": True,
    }


class DomainEvaluator:
    """Evaluator for vertical domain evaluation using dual-prompt system."""

    def __init__(self, generation_prompts: list[str], evaluation_prompts: list[str]):
        self.gen_prompts = generation_prompts
        self.eval_prompts = evaluation_prompts

    def evaluate(self, provider, judge_provider, sample: dict) -> dict:
        """
        1. Render generation prompt with sample input
        2. Run tested model to get output
        3. Render evaluation prompt with input + output + model_output
        4. Run judge model to score
        """
        # Extract input: handle Alpaca-style (instruction+input) and other formats
        instruction = sample.get("instruction", "")
        supplementary_input = sample.get("input", "")
        if instruction and supplementary_input:
            input_text = f"{instruction}\n\n{supplementary_input}"
        elif instruction:
            input_text = instruction
        else:
            input_text = (
                supplementary_input or
                sample.get("question") or
                sample.get("prompt") or
                sample.get("text", "")
            )

        # Extract reference answer from dataset
        reference = (
            sample.get("output") or
            sample.get("answer") or
            sample.get("reference") or
            sample.get("expected", "")
        )
        if isinstance(reference, (list, dict)):
            import json as _json
            reference = _json.dumps(reference, ensure_ascii=False)

        # 1. Pick the first generation prompt and render
        gen_prompt = self.gen_prompts[0] if self.gen_prompts else input_text
        gen_prompt = gen_prompt.replace("{{input}}", input_text)

        # 2. Generate output from tested model
        gen_result = provider.complete(gen_prompt)
        model_output = gen_result.get("output", "")
        latency_ms = gen_result.get("latency_ms", 0)
        prompt_tokens = gen_result.get("prompt_tokens", 0)
        completion_tokens = gen_result.get("completion_tokens", 0)

        # 3. Build evaluation prompt — support all variable placeholders:
        #    {{input}} = user question, {{output}} = reference answer, {{model_output}} = tested model's output
        eval_prompt_template = self.eval_prompts[0] if self.eval_prompts else "请评估回答的质量和准确性。"
        eval_prompt_rendered = (
            eval_prompt_template
            .replace("{{input}}", input_text)
            .replace("{{output}}", reference or "无标准参考答案")
            .replace("{{model_output}}", model_output)
        )

        # 4. Build full judge prompt
        # If user's eval prompt already contains structured scoring instructions (JSON format request),
        # use it directly instead of wrapping with JUDGE_SCORE_PROMPT to avoid double-wrapping
        has_json_format = "json" in eval_prompt_rendered.lower() or '"overall"' in eval_prompt_rendered
        if has_json_format:
            full_judge_prompt = eval_prompt_rendered
        else:
            full_judge_prompt = JUDGE_SCORE_PROMPT.format(
                input=input_text,
                output=model_output,
                eval_prompt=eval_prompt_rendered,
            )

        # 5. Judge model scores
        judge_result = judge_provider.complete(full_judge_prompt)
        parsed = parse_judge_scores(judge_result.get("output", ""))

        # Build scores dict
        scores = {"domain_overall": parsed["overall"]}
        for dim_name, dim_val in parsed.get("dimensions", {}).items():
            if isinstance(dim_val, (int, float)):
                scores[f"domain_{dim_name}"] = float(dim_val)

        return {
            "output": model_output,
            "scores": scores,
            "metadata": {
                "judge_reasoning": parsed.get("reasoning", ""),
                "problems": parsed.get("problems", []),
                "gen_prompt_used": gen_prompt[:300],
                "eval_prompt_used": eval_prompt_rendered[:300],
            },
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }
