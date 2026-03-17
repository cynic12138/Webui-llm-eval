"""
Instruction-following evaluator.
Tests how well a model follows specific constraints in instructions:
format, length, language, keyword inclusion/exclusion, etc.
"""
import re
from typing import Optional


BUILTIN_SAMPLES = [
    # --- English samples (3) ---
    {
        "instruction": "List exactly 3 benefits of exercise. Use bullet points starting with '-'. Each bullet must be one sentence.",
        "constraints": [
            {"type": "format", "pattern": r"^- .+", "description": "bullet points starting with '-'"},
            {"type": "count", "pattern": r"^- ", "expected": 3, "description": "exactly 3 bullets"},
        ],
    },
    {
        "instruction": "Write a haiku about the ocean. It must be exactly 3 lines. Do not use the word 'water'.",
        "constraints": [
            {"type": "line_count", "expected": 3, "description": "exactly 3 lines"},
            {"type": "keyword_exclusion", "keywords": ["water"], "description": "must not contain 'water'"},
        ],
    },
    {
        "instruction": "Explain photosynthesis in exactly two sentences. Include the words 'sunlight' and 'carbon dioxide'.",
        "constraints": [
            {"type": "sentence_count", "expected": 2, "description": "exactly 2 sentences"},
            {"type": "keyword_inclusion", "keywords": ["sunlight", "carbon dioxide"], "description": "must include required keywords"},
        ],
    },
    # --- Chinese samples (7) ---
    {
        "instruction": "请用数字编号（1. 2. 3.）列出阅读的3个好处，每条一句话。",
        "constraints": [
            {"type": "format", "pattern": r"^\d+\.", "description": "使用数字编号格式（如 1. 2. 3.）"},
            {"type": "count", "pattern": r"^\d+\.", "expected": 3, "description": "恰好列出3条"},
        ],
    },
    {
        "instruction": "用不超过50个字回答：为什么天空是蓝色的？",
        "constraints": [
            {"type": "max_words", "max": 50, "description": "回答不超过50个词"},
        ],
    },
    {
        "instruction": "请用逗号分隔的方式，在一行内列出五种常见水果，必须包含'苹果'和'香蕉'。",
        "constraints": [
            {"type": "line_count", "expected": 1, "description": "输出必须为一行"},
            {"type": "keyword_inclusion", "keywords": ["苹果", "香蕉"], "description": "必须包含'苹果'和'香蕉'"},
        ],
    },
    {
        "instruction": "请写一首关于春天的四行中文诗，每行不超过十个字。",
        "constraints": [
            {"type": "line_count", "expected": 4, "description": "必须恰好四行"},
            {"type": "language", "language": "zh", "description": "必须使用中文"},
        ],
    },
    {
        "instruction": "请完全使用中文解释什么是人工智能，不要使用任何英文单词。",
        "constraints": [
            {"type": "language", "language": "zh", "description": "必须完全使用中文，不使用英文"},
        ],
    },
    {
        "instruction": "请描述冬天的特点，不要使用'寒冷'和'下雪'这两个词。",
        "constraints": [
            {"type": "keyword_exclusion", "keywords": ["寒冷", "下雪"], "description": "不得包含'寒冷'和'下雪'"},
        ],
    },
    {
        "instruction": "请详细解释量子计算的基本原理，回答至少使用100个词。",
        "constraints": [
            {"type": "min_words", "min": 100, "description": "回答至少100个词"},
        ],
    },
]


class InstructionFollowingEvaluator:
    def __init__(self):
        pass

    def evaluate(self, provider, sample: dict) -> dict:
        """
        Evaluate instruction following.

        sample:
            instruction: str - the instruction to give the model
            constraints: list[dict] - constraints to check against the output
        """
        instruction = sample.get("instruction", "")
        constraints = sample.get("constraints", [])

        result = provider.complete(instruction)
        output = result["output"].strip()

        passed = 0
        total = len(constraints)
        constraint_results = []

        for constraint in constraints:
            ok = self._check_constraint(output, constraint)
            if ok:
                passed += 1
            constraint_results.append({
                "description": constraint.get("description", constraint.get("type", "")),
                "passed": ok,
            })

        strict_score = passed / total if total > 0 else 1.0

        return {
            "output": output,
            "scores": {
                "ifeval_strict": strict_score,
            },
            "metadata": {
                "constraints_passed": passed,
                "constraints_total": total,
                "constraint_results": constraint_results,
            },
            **{k: v for k, v in result.items() if k != "output"},
        }

    def get_builtin_samples(self) -> list:
        return BUILTIN_SAMPLES

    def _check_constraint(self, output: str, constraint: dict) -> bool:
        ctype = constraint.get("type", "")

        if ctype == "format":
            pattern = constraint.get("pattern", "")
            return bool(re.search(pattern, output, re.MULTILINE))

        elif ctype == "count":
            pattern = constraint.get("pattern", "")
            expected = constraint.get("expected", 0)
            matches = re.findall(pattern, output, re.MULTILINE)
            return len(matches) == expected

        elif ctype == "line_count":
            expected = constraint.get("expected", 0)
            lines = [l for l in output.strip().split("\n") if l.strip()]
            return len(lines) == expected

        elif ctype == "sentence_count":
            expected = constraint.get("expected", 0)
            sentences = re.split(r'(?<=[.!?])\s+', output.strip())
            sentences = [s for s in sentences if s.strip()]
            return len(sentences) == expected

        elif ctype == "keyword_inclusion":
            keywords = constraint.get("keywords", [])
            output_lower = output.lower()
            return all(kw.lower() in output_lower for kw in keywords)

        elif ctype == "keyword_exclusion":
            keywords = constraint.get("keywords", [])
            output_lower = output.lower()
            return all(kw.lower() not in output_lower for kw in keywords)

        elif ctype == "max_words":
            max_words = constraint.get("max", 100)
            return len(output.split()) <= max_words

        elif ctype == "min_words":
            min_words = constraint.get("min", 1)
            return len(output.split()) >= min_words

        elif ctype == "language":
            expected_lang = constraint.get("language", "en")
            return self._check_language(output, expected_lang)

        elif ctype == "regex":
            pattern = constraint.get("pattern", "")
            return bool(re.search(pattern, output))

        return False

    def _check_language(self, text: str, expected: str) -> bool:
        """Simple heuristic language detection."""
        if expected == "en":
            ascii_chars = sum(1 for c in text if ord(c) < 128)
            return ascii_chars / max(len(text), 1) > 0.8
        elif expected == "zh":
            cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            return cjk / max(len(text.replace(" ", "")), 1) > 0.3
        return True
