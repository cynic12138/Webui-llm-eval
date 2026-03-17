"""
Hallucination detection via consistency sampling.
Ask the same question N times and measure answer agreement.
"""
import re
from typing import Optional


class HallucinationEvaluator:
    def __init__(self, n_samples: int = 5):
        self.n_samples = n_samples

    def evaluate(self, provider, input_text: str) -> dict:
        """
        Sample the model n_samples times and compute consistency score.
        Higher = more consistent (less hallucination risk).
        """
        outputs = []
        for _ in range(self.n_samples):
            result = provider.complete(input_text, **{"temperature": 0.7})
            outputs.append(result["output"])

        consistency = self._compute_consistency(outputs)
        return {
            "hallucination_consistency": consistency,
            "hallucination_risk": 1.0 - consistency,
            "n_samples": self.n_samples,
            "samples": outputs[:3],  # Keep first 3 for inspection
        }

    def _compute_consistency(self, outputs: list) -> float:
        """Compute pairwise similarity across outputs."""
        if len(outputs) < 2:
            return 1.0

        # Extract key facts/numbers from each output
        facts_per_output = [self._extract_key_facts(o) for o in outputs]

        # Compute pairwise Jaccard similarity
        similarities = []
        for i in range(len(facts_per_output)):
            for j in range(i + 1, len(facts_per_output)):
                sim = self._jaccard(facts_per_output[i], facts_per_output[j])
                similarities.append(sim)

        return sum(similarities) / len(similarities) if similarities else 0.0

    def _extract_key_facts(self, text: str) -> set:
        """Extract numbers and key noun phrases as facts."""
        facts = set()
        # Numbers
        numbers = re.findall(r'\b\d+\.?\d*\b', text)
        facts.update(numbers)
        # Capitalized terms (entities)
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b', text)
        facts.update(e.lower() for e in entities)
        # Words > 5 chars (content words)
        words = re.findall(r'\b[a-z]{5,}\b', text.lower())
        facts.update(words[:20])  # Limit to avoid noise
        return facts

    def _jaccard(self, a: set, b: set) -> float:
        if not a and not b:
            return 1.0
        intersection = len(a & b)
        union = len(a | b)
        return intersection / union if union > 0 else 0.0
