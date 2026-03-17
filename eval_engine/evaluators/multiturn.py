"""
Multi-turn conversation evaluation.
"""
from typing import Optional


class MultiturnEvaluator:
    def evaluate(self, provider, conversation: list) -> dict:
        """
        conversation: [{"role": "user"|"assistant", "content": "..."}]
        Evaluate coherence and quality across turns.
        """
        history = []
        responses = []

        for turn in conversation:
            if turn["role"] == "user":
                # Build prompt with history
                prompt = self._build_prompt(turn["content"], history)
                result = provider.complete(prompt)
                response = result["output"]
                history.append({"role": "user", "content": turn["content"]})
                history.append({"role": "assistant", "content": response})
                responses.append(response)
            elif turn["role"] == "assistant":
                # Use provided reference response
                history.append(turn)

        coherence = self._measure_coherence(responses)
        return {
            "multiturn_coherence": coherence,
            "n_turns": len(responses),
            "responses": responses[:3],
        }

    def _build_prompt(self, current: str, history: list) -> str:
        if not history:
            return current
        history_text = "\n".join(
            f"{t['role'].capitalize()}: {t['content']}" for t in history[-6:]  # Last 3 exchanges
        )
        return f"{history_text}\nUser: {current}"

    def _measure_coherence(self, responses: list) -> float:
        """Simple coherence: no repetition and reasonable length."""
        if not responses:
            return 0.0
        if len(responses) == 1:
            return 0.8

        # Check for repetition
        unique_responses = len(set(responses))
        diversity = unique_responses / len(responses)

        # Average response length (should be reasonable)
        avg_len = sum(len(r.split()) for r in responses) / len(responses)
        length_score = min(avg_len / 20.0, 1.0)

        return (diversity + length_score) / 2
