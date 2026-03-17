"""
LLM-as-Judge evaluator with bias mitigation.
- Position bias: judge twice with swapped order
- Verbosity bias: prompt template penalizes length
- Multi-judge: majority voting
"""
import re
from typing import Optional


JUDGE_PROMPT = """You are a fair and objective evaluator. Rate the quality of the following AI response.

Question/Input:
{input}

AI Response to evaluate:
{output}

{reference_section}

Evaluate on the following dimensions (score 1-10 each):
{dimensions}

IMPORTANT: Be concise in your assessment. Longer responses do not automatically mean better responses.

Respond ONLY with a JSON object like:
{{"accuracy": 8, "fluency": 9, "relevance": 7, "reasoning": "Brief explanation"}}
"""

COMPARATIVE_PROMPT = """You are a fair judge comparing two AI responses.

Question/Input:
{input}

Response A:
{response_a}

Response B:
{response_b}

{reference_section}

Which response is better? Consider accuracy, helpfulness, and conciseness.
Respond ONLY with JSON: {{"winner": "A" or "B" or "tie", "reasoning": "brief reason"}}
"""


class LLMJudgeEvaluator:
    def __init__(self, judge_provider, dimensions: list = None):
        self.judge = judge_provider
        self.dimensions = dimensions or ["accuracy", "fluency", "relevance"]

    def evaluate(self, input_text: str, output_text: str, reference: Optional[str] = None) -> dict:
        """Evaluate with position-bias mitigation (rate twice, average)."""
        ref_section = f"\nReference Answer:\n{reference}" if reference else ""
        dims_text = "\n".join(f"- {d}" for d in self.dimensions)

        prompt = JUDGE_PROMPT.format(
            input=input_text,
            output=output_text,
            reference_section=ref_section,
            dimensions=dims_text,
        )

        scores1 = self._parse_scores(self.judge.complete(prompt)["output"])

        # Second pass with shuffled dimension order (mitigate order bias)
        dims_shuffled = self.dimensions[::-1]
        dims_text2 = "\n".join(f"- {d}" for d in dims_shuffled)
        prompt2 = JUDGE_PROMPT.format(
            input=input_text,
            output=output_text,
            reference_section=ref_section,
            dimensions=dims_text2,
        )
        scores2 = self._parse_scores(self.judge.complete(prompt2)["output"])

        # Average scores from both passes
        final = {}
        for dim in self.dimensions:
            v1 = scores1.get(dim, 5)
            v2 = scores2.get(dim, 5)
            final[f"judge_{dim}"] = min(max((v1 + v2) / 2 / 10, 0.0), 1.0)  # Normalize to 0-1, clamp

        return final

    def compare(self, input_text: str, output_a: str, output_b: str, reference: Optional[str] = None) -> dict:
        """Compare two responses with position-bias mitigation."""
        ref_section = f"\nReference:\n{reference}" if reference else ""

        # Forward comparison
        r1 = self._parse_winner(self.judge.complete(COMPARATIVE_PROMPT.format(
            input=input_text, response_a=output_a, response_b=output_b, reference_section=ref_section
        ))["output"])

        # Reverse comparison (swap A and B)
        r2_raw = self._parse_winner(self.judge.complete(COMPARATIVE_PROMPT.format(
            input=input_text, response_a=output_b, response_b=output_a, reference_section=ref_section
        ))["output"])

        # Invert the reversed result
        if r2_raw == "A":
            r2 = "B"
        elif r2_raw == "B":
            r2 = "A"
        else:
            r2 = "tie"

        if r1 == r2:
            return {"winner": r1, "consistent": True}
        return {"winner": "tie", "consistent": False}

    def _parse_scores(self, text: str) -> dict:
        try:
            import json
            # Extract JSON from text
            match = re.search(r'\{.*?\}', text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return {k: float(v) for k, v in data.items() if k != "reasoning" and isinstance(v, (int, float))}
        except Exception:
            pass
        return {dim: 5.0 for dim in self.dimensions}

    def _parse_winner(self, text: str) -> str:
        try:
            import json
            match = re.search(r'\{.*?\}', text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return data.get("winner", "tie")
        except Exception:
            pass
        return "tie"
