"""
Robustness evaluator - tests model stability under input perturbations.
"""
import random
import re
from typing import Optional


class RobustnessEvaluator:
    def __init__(self, perturbations: list = None):
        self.perturbations = perturbations or ["synonym", "typo", "case"]

    def evaluate(self, provider, input_text: str, reference_output: Optional[str] = None) -> dict:
        """Evaluate robustness across perturbations."""
        original_result = provider.complete(input_text)
        original_output = original_result["output"]

        perturbed_outputs = []
        for ptype in self.perturbations:
            perturbed_input = self._perturb(input_text, ptype)
            try:
                perturbed_result = provider.complete(perturbed_input)
                perturbed_output = perturbed_result["output"]
            except Exception:
                perturbed_output = ""

            similarity = self._compute_similarity(original_output, perturbed_output)
            perturbed_outputs.append({
                "perturbation": ptype,
                "perturbed_input": perturbed_input[:200],
                "similarity": similarity,
            })

        avg_robustness = sum(p["similarity"] for p in perturbed_outputs) / len(perturbed_outputs) if perturbed_outputs else 1.0

        return {
            "robustness_score": avg_robustness,
            "perturbation_details": perturbed_outputs,
        }

    def _perturb(self, text: str, ptype: str) -> str:
        if ptype == "typo":
            return self._add_typos(text)
        elif ptype == "case":
            return text.lower()
        elif ptype == "synonym":
            return self._synonym_replacement(text)
        elif ptype == "shuffle":
            return self._shuffle_sentences(text)
        return text

    def _add_typos(self, text: str, rate: float = 0.05) -> str:
        """Randomly swap adjacent characters."""
        chars = list(text)
        for i in range(len(chars) - 1):
            if random.random() < rate and chars[i].isalpha():
                chars[i], chars[i + 1] = chars[i + 1], chars[i]
        return "".join(chars)

    def _synonym_replacement(self, text: str) -> str:
        """Simple synonym replacement using a small dictionary."""
        synonyms = {
            "good": "excellent", "bad": "poor", "big": "large", "small": "tiny",
            "fast": "quick", "slow": "sluggish", "happy": "pleased", "sad": "unhappy",
            "get": "obtain", "use": "utilize", "make": "create", "show": "demonstrate",
            "tell": "inform", "give": "provide", "find": "discover", "need": "require",
        }
        words = text.split()
        return " ".join(synonyms.get(w.lower(), w) for w in words)

    def _shuffle_sentences(self, text: str) -> str:
        """Shuffle sentence order."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) > 1:
            mid = len(sentences) // 2
            sentences = sentences[mid:] + sentences[:mid]
        return " ".join(sentences)

    def _compute_similarity(self, text1: str, text2: str) -> float:
        """Token-level Jaccard similarity."""
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())
        if not tokens1 and not tokens2:
            return 1.0
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        return intersection / union if union > 0 else 0.0
