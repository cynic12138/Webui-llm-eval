"""
Self-consistency evaluator - run multiple times at temp > 0 and check agreement.
"""


class ConsistencyEvaluator:
    def __init__(self, n_runs: int = 3):
        self.n_runs = n_runs

    def evaluate(self, provider, input_text: str) -> dict:
        """Run the model n_runs times and measure output consistency."""
        outputs = []
        for _ in range(self.n_runs):
            result = provider.complete(input_text, temperature=0.7)
            outputs.append(result["output"])

        consistency = self._measure_consistency(outputs)
        return {
            "consistency_score": consistency,
            "n_runs": self.n_runs,
        }

    def _measure_consistency(self, outputs: list) -> float:
        """Measure average pairwise token similarity."""
        if len(outputs) < 2:
            return 1.0

        similarities = []
        for i in range(len(outputs)):
            for j in range(i + 1, len(outputs)):
                t1 = set(outputs[i].lower().split())
                t2 = set(outputs[j].lower().split())
                union = len(t1 | t2)
                if union == 0:
                    sim = 1.0
                else:
                    sim = len(t1 & t2) / union
                similarities.append(sim)

        return sum(similarities) / len(similarities)
