"""
Long-context (needle-in-a-haystack) evaluator.
Embeds a specific fact ("needle") at a configurable depth within filler text,
then asks the model to retrieve that fact.
"""
import random
from typing import Optional


FILLER_PARAGRAPHS = [
    "The history of maritime navigation spans thousands of years, from ancient Polynesian wayfinding to modern GPS systems. Early sailors relied on stars, ocean currents, and the behavior of seabirds to find their way across vast stretches of open water.",
    "Advances in agricultural technology during the 20th century dramatically increased global food production. The Green Revolution introduced high-yield crop varieties, synthetic fertilizers, and improved irrigation techniques to developing nations.",
    "Classical music evolved through several distinct periods, from the Baroque era of Bach and Vivaldi to the Romantic period of Chopin and Liszt. Each era brought new forms, instruments, and compositional techniques.",
    "The study of volcanology involves monitoring seismic activity, gas emissions, and ground deformation to predict eruptions. Modern instruments can detect subtle changes deep within the Earth's crust.",
    "Renaissance art marked a dramatic shift toward realism, perspective, and humanism. Artists like Leonardo da Vinci and Michelangelo revolutionized painting and sculpture with their mastery of anatomy and light.",
    "The development of antibiotics in the 20th century transformed medicine. Alexander Fleming's discovery of penicillin in 1928 opened the door to treating bacterial infections that had been fatal for centuries.",
    "Quantum computing leverages quantum mechanical phenomena like superposition and entanglement to process information in fundamentally different ways than classical computers.",
    "The Amazon rainforest, spanning nine countries in South America, contains roughly ten percent of all species on Earth. Its dense canopy creates a complex ecosystem of interdependent organisms.",
    "Ancient Roman engineering achievements include aqueducts, roads, and concrete structures that have endured for millennia. The Pantheon's unreinforced concrete dome remains the largest of its kind.",
    "The field of behavioral economics studies how psychological factors influence economic decisions. Research by Kahneman and Tversky revealed systematic biases in human judgment and decision-making.",
    "Deep-sea exploration has revealed extraordinary life forms adapted to extreme pressure, darkness, and cold. Hydrothermal vents support chemosynthetic ecosystems independent of solar energy.",
    "The invention of the printing press by Gutenberg around 1440 democratized knowledge and catalyzed the Protestant Reformation, the Scientific Revolution, and the Age of Enlightenment.",
    "Modern cryptography relies on mathematical problems that are easy to compute in one direction but practically impossible to reverse, such as the factoring of large prime numbers.",
    "The human microbiome consists of trillions of microorganisms that play crucial roles in digestion, immune function, and even mental health. Research in this area is reshaping our understanding of disease.",
    "Glacier retreat is one of the most visible indicators of climate change. Since the mid-19th century, glaciers worldwide have lost significant mass, contributing to rising sea levels.",
    "The principles of aerodynamics govern the design of aircraft, from the Wright brothers' first powered flight in 1903 to modern supersonic jets and unmanned aerial vehicles.",
]

DEFAULT_NEEDLES = [
    {"needle": "The secret project code name is Operation Nightingale, established on March 15, 2019.", "question": "What is the secret project code name and when was it established?", "answer": "Operation Nightingale, established on March 15, 2019"},
    {"needle": "The vault combination is 7-23-42-58, given to Agent Roberts on a Tuesday.", "question": "What is the vault combination?", "answer": "7-23-42-58"},
    {"needle": "Dr. Elena Vasquez discovered that compound XR-7 reduces inflammation by 87% in clinical trials.", "question": "What percentage does compound XR-7 reduce inflammation by?", "answer": "87%"},
    {"needle": "根据2024年国际气象组织的报告，全球平均海平面在过去十年中上升了3.7厘米。", "question": "根据2024年国际气象组织的报告，全球平均海平面上升了多少？", "answer": "3.7厘米"},
    {"needle": "中国古代四大发明分别是造纸术、印刷术、火药和指南针，其中造纸术最早由蔡伦在公元105年改进。", "question": "蔡伦在哪一年改进了造纸术？", "answer": "公元105年"},
    {"needle": "2023年诺贝尔物理学奖授予了皮埃尔·阿戈斯蒂尼、费伦茨·克劳斯和安妮·吕利耶，以表彰他们在阿秒光脉冲方面的贡献。", "question": "2023年诺贝尔物理学奖表彰了什么领域的贡献？", "answer": "阿秒光脉冲"},
]


class LongContextEvaluator:
    def __init__(self, context_length: int = 4000, needle_depth: float = 0.5):
        """
        context_length: approximate target context length in characters
        needle_depth: 0.0 = beginning, 0.5 = middle, 1.0 = end
        """
        self.context_length = context_length
        self.needle_depth = max(0.0, min(1.0, needle_depth))

    def evaluate(self, provider, config: Optional[dict] = None) -> dict:
        """
        Run needle-in-a-haystack test.

        config (optional):
            needle: str - the fact to embed
            question: str - question to ask about the needle
            answer: str - expected answer
            context_length: int - override default context length
            needle_depth: float - override default needle depth
        """
        config = config or {}
        needle_info = config if "needle" in config else random.choice(DEFAULT_NEEDLES)
        needle = needle_info["needle"]
        question = needle_info["question"]
        expected_answer = needle_info["answer"]

        ctx_len = config.get("context_length", self.context_length)
        depth = config.get("needle_depth", self.needle_depth)

        # Build context with needle inserted
        context = self._build_context(needle, ctx_len, depth)

        prompt = (
            f"Read the following text carefully and answer the question at the end.\n\n"
            f"--- BEGIN TEXT ---\n{context}\n--- END TEXT ---\n\n"
            f"Question: {question}\n"
            f"Answer concisely based only on the text above:"
        )

        result = provider.complete(prompt)
        output = result["output"].strip()

        # Check if the model retrieved the needle
        retrieval_success = self._check_retrieval(output, expected_answer)

        # Estimate token count (rough: 1 token ~ 4 chars)
        approx_context_tokens = len(context) // 4

        return {
            "output": output,
            "scores": {
                "needle_retrieval": 1.0 if retrieval_success else 0.0,
            },
            "metadata": {
                "needle": needle,
                "question": question,
                "expected_answer": expected_answer,
                "needle_depth": depth,
                "context_chars": len(context),
                "context_tokens": approx_context_tokens,
                "approx_context_tokens": approx_context_tokens,
                "retrieval_success": retrieval_success,
            },
            **{k: v for k, v in result.items() if k != "output"},
        }

    def _build_context(self, needle: str, target_length: int, depth: float) -> str:
        """Build filler text with needle inserted at the specified depth."""
        paragraphs = list(FILLER_PARAGRAPHS)

        # Repeat paragraphs until we reach target length
        context_parts = []
        total_len = 0
        idx = 0
        while total_len < target_length:
            para = paragraphs[idx % len(paragraphs)]
            context_parts.append(para)
            total_len += len(para) + 2  # +2 for newlines
            idx += 1

        # Calculate insertion position
        insert_pos = max(1, int(len(context_parts) * depth))
        insert_pos = min(insert_pos, len(context_parts))

        context_parts.insert(insert_pos, needle)

        return "\n\n".join(context_parts)

    def _check_retrieval(self, output: str, expected: str) -> bool:
        """Check if the model's output contains the expected answer."""
        output_lower = output.lower().strip()
        expected_lower = expected.lower().strip()

        # Direct containment
        if expected_lower in output_lower:
            return True

        # Check key terms from the expected answer
        key_terms = [t for t in expected_lower.split() if len(t) > 3]
        if not key_terms:
            key_terms = expected_lower.split()

        matched = sum(1 for term in key_terms if term in output_lower)
        return matched >= len(key_terms) * 0.7

    def get_builtin_needles(self) -> list:
        return DEFAULT_NEEDLES
