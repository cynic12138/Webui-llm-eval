"""
Chain-of-thought reasoning evaluator.
Analyzes whether the model produces step-by-step reasoning and whether
the final answer is correct.
"""
import re
from typing import Optional


COT_MARKERS = [
    r"step\s*\d",
    r"first[,:]",
    r"second[,:]",
    r"third[,:]",
    r"next[,:]",
    r"then[,:]",
    r"finally[,:]",
    r"therefore[,:]",
    r"because\b",
    r"since\b",
    r"let'?s\s+(think|break|consider|analyze|solve)",
    r"we\s+(know|can|need|have|see)\s+that",
    r"\bso\b.*\b(means|implies|gives)\b",
    r"=>",
    r"thus[,:]",
]

BUILTIN_SAMPLES = [
    {
        "problem": "A farmer has 15 chickens and 8 cows. How many legs do the animals have in total?",
        "reference_answer": "62",
    },
    {
        "problem": "If a shirt originally costs $40 and is 25% off, what is the sale price?",
        "reference_answer": "30",
    },
    {
        "problem": "A train leaves City A at 9am traveling at 60 mph. Another train leaves City B (180 miles away) at 10am toward City A at 90 mph. At what time do they meet?",
        "reference_answer": "11",
    },
    {
        "problem": "小明有15个苹果，给了小红3个，又买了8个，现在有多少个？",
        "reference_answer": "20",
    },
    {
        "problem": "一个长方形长12厘米宽5厘米，周长是多少厘米？",
        "reference_answer": "34",
    },
    {
        "problem": "鸡兔同笼，共有头35个，脚94只，问鸡和兔各有多少只？",
        "reference_answer": "鸡23只，兔12只",
    },
    {
        "problem": "一列火车从A站出发，速度60公里/小时，另一列从B站出发，速度80公里/小时，A和B相距280公里，两车相向而行，几小时后相遇？",
        "reference_answer": "2",
    },
    {
        "problem": "一个商品原价200元，先打八折，再打九折，最终价格是多少？",
        "reference_answer": "144",
    },
]


class ChainOfThoughtEvaluator:
    def __init__(self):
        pass

    def evaluate(self, provider, sample: dict) -> dict:
        """
        Evaluate chain-of-thought reasoning.

        sample:
            problem: str - a problem requiring reasoning
            reference_answer: str (optional) - expected final answer for correctness check
        """
        problem = sample.get("problem", "")
        reference = sample.get("reference_answer", None)

        prompt = (
            f"Solve the following problem step by step. Show your reasoning, "
            f"then give your final answer on a line starting with 'Answer:'.\n\n"
            f"Problem: {problem}\n\nSolution:"
        )

        result = provider.complete(prompt)
        output = result["output"].strip()

        # Count reasoning steps
        step_count = self._count_steps(output)

        # Check if reasoning markers are present
        has_reasoning = self._has_reasoning(output)

        # Check answer correctness if reference is provided
        answer_correct = 0
        extracted_answer = self._extract_answer(output)
        if reference is not None:
            answer_correct = 1 if self._answers_match(extracted_answer, reference) else 0

        scores = {
            "cot_step_count": float(step_count),
            "cot_has_reasoning": 1.0 if has_reasoning else 0.0,
            "cot_answer_correct": float(answer_correct),
        }

        return {
            "output": output,
            "scores": scores,
            "metadata": {
                "step_count": step_count,
                "has_reasoning": has_reasoning,
                "extracted_answer": extracted_answer,
                "reference_answer": reference,
            },
            **{k: v for k, v in result.items() if k != "output"},
        }

    def get_builtin_samples(self) -> list:
        return BUILTIN_SAMPLES

    def _count_steps(self, text: str) -> int:
        """Count the number of reasoning steps in the output."""
        # Look for explicit step numbering
        numbered_steps = re.findall(r'(?:step|Stage)\s*(\d+)', text, re.IGNORECASE)
        if numbered_steps:
            return max(int(n) for n in numbered_steps)

        # Look for numbered list items (1. 2. 3.)
        numbered_list = re.findall(r'^\s*(\d+)[.)]\s+', text, re.MULTILINE)
        if len(numbered_list) >= 2:
            return len(numbered_list)

        # Fall back to counting sentences that contain reasoning markers
        sentences = re.split(r'(?<=[.!?])\s+', text)
        reasoning_sentences = 0
        for sentence in sentences:
            for marker in COT_MARKERS:
                if re.search(marker, sentence, re.IGNORECASE):
                    reasoning_sentences += 1
                    break
        return max(reasoning_sentences, 1) if sentences else 0

    def _has_reasoning(self, text: str) -> bool:
        """Check if the output contains step-by-step reasoning."""
        marker_count = 0
        for marker in COT_MARKERS:
            if re.search(marker, text, re.IGNORECASE):
                marker_count += 1
        # Require at least 2 different reasoning markers
        return marker_count >= 2

    def _extract_answer(self, text: str) -> str:
        """Extract the final answer from the output."""
        # Try to find explicit "Answer:" line
        answer_match = re.search(
            r'(?:Answer|Final Answer|The answer is|Result)\s*[:=]\s*\$?([-\d.,]+)',
            text, re.IGNORECASE
        )
        if answer_match:
            return answer_match.group(1).replace(",", "").strip()

        # Try to find the last number in the text
        numbers = re.findall(r'[-]?\d+\.?\d*', text)
        if numbers:
            return numbers[-1]

        return ""

    def _answers_match(self, predicted: str, reference: str) -> bool:
        """Compare predicted and reference answers numerically or by string."""
        predicted = predicted.strip().rstrip(".")
        reference = reference.strip().rstrip(".")

        # Direct string match
        if predicted.lower() == reference.lower():
            return True

        # Numeric comparison
        try:
            pred_val = float(predicted.replace(",", ""))
            ref_val = float(reference.replace(",", ""))
            return abs(pred_val - ref_val) < 0.01
        except ValueError:
            pass

        # Check if reference is contained in predicted
        return reference.lower() in predicted.lower()
