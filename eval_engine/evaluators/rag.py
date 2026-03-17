"""
RAG evaluation: Faithfulness and Relevance.
"""
import re
from typing import Optional


FAITHFULNESS_PROMPT = """Given the following context and answer, evaluate if the answer is faithful to the context (does not make up facts not in the context).

Context:
{context}

Answer:
{answer}

Is every claim in the answer supported by the context? Respond with JSON:
{{"faithfulness": 0.0-1.0, "issues": "list any hallucinated claims or None"}}"""

RELEVANCE_PROMPT = """Given the following question and answer, rate how relevant the answer is to the question.

Question: {question}
Answer: {answer}

Respond with JSON: {{"relevance": 0.0-1.0, "reasoning": "brief reason"}}"""


class RAGEvaluator:
    def __init__(self, judge_provider=None):
        self.judge = judge_provider

    def evaluate(self, question: str, answer: str, context: Optional[str] = None) -> dict:
        scores = {}

        # Faithfulness (requires context)
        if context and self.judge:
            scores["rag_faithfulness"] = self._evaluate_faithfulness(context, answer)

        # Relevance
        if self.judge:
            scores["rag_relevance"] = self._evaluate_relevance(question, answer)
        else:
            scores["rag_relevance"] = self._simple_relevance(question, answer)

        # Answer completeness (length heuristic)
        scores["rag_completeness"] = min(len(answer.split()) / 50.0, 1.0)

        return scores

    def _evaluate_faithfulness(self, context: str, answer: str) -> float:
        prompt = FAITHFULNESS_PROMPT.format(context=context[:2000], answer=answer)
        try:
            result = self.judge.complete(prompt)
            match = re.search(r'"faithfulness":\s*([\d.]+)', result["output"])
            if match:
                return float(match.group(1))
        except Exception:
            pass
        return 0.5

    def _evaluate_relevance(self, question: str, answer: str) -> float:
        prompt = RELEVANCE_PROMPT.format(question=question, answer=answer)
        try:
            result = self.judge.complete(prompt)
            match = re.search(r'"relevance":\s*([\d.]+)', result["output"])
            if match:
                return float(match.group(1))
        except Exception:
            pass
        return self._simple_relevance(question, answer)

    def _simple_relevance(self, question: str, answer: str) -> float:
        """Keyword overlap as simple relevance metric."""
        q_words = set(question.lower().split()) - {"the", "a", "an", "is", "are", "was", "were", "what", "how", "why", "when", "where", "who"}
        a_words = set(answer.lower().split())
        if not q_words:
            return 0.5
        overlap = len(q_words & a_words) / len(q_words)
        return min(overlap, 1.0)
