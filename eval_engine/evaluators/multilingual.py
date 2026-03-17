"""
Multilingual evaluator.
Sends the same prompt in multiple languages and evaluates response quality
for each, producing per-language and aggregate scores.
"""
import re
from typing import Optional


DEFAULT_LANGUAGES = ["en", "zh", "ja", "ko", "fr", "de", "es"]

# Translation templates for a simple knowledge question
PROMPTS_BY_LANG = {
    "en": "What is the capital of France? Answer in one sentence.",
    "zh": "法国的首都是哪里？请用一句话回答。",
    "ja": "フランスの首都はどこですか？一文で答えてください。",
    "ko": "프랑스의 수도는 어디입니까? 한 문장으로 답하세요.",
    "fr": "Quelle est la capitale de la France ? Répondez en une phrase.",
    "de": "Was ist die Hauptstadt von Frankreich? Antworten Sie in einem Satz.",
    "es": "¿Cuál es la capital de Francia? Responde en una oración.",
}

# Expected answer keywords per language
EXPECTED_KEYWORDS = {
    "en": ["paris"],
    "zh": ["巴黎"],
    "ja": ["パリ"],
    "ko": ["파리"],
    "fr": ["paris"],
    "de": ["paris"],
    "es": ["paris", "parís"],
}

BUILTIN_SAMPLES = [
    {
        "prompts": PROMPTS_BY_LANG,
        "expected_keywords": EXPECTED_KEYWORDS,
        "description": "Capital of France",
    },
    {
        "prompts": {
            "en": "What is 15 multiplied by 4? Answer with just the number.",
            "zh": "15乘以4等于多少？只回答数字。",
            "ja": "15かける4はいくつですか？数字だけで答えてください。",
            "ko": "15 곱하기 4는 얼마입니까? 숫자만 답하세요.",
            "fr": "Combien fait 15 multiplié par 4 ? Répondez avec le nombre uniquement.",
            "de": "Was ist 15 mal 4? Antworten Sie nur mit der Zahl.",
            "es": "¿Cuánto es 15 multiplicado por 4? Responde solo con el número.",
        },
        "expected_keywords": {
            "en": ["60"], "zh": ["60"], "ja": ["60"],
            "ko": ["60"], "fr": ["60"], "de": ["60"], "es": ["60"],
        },
        "description": "Simple multiplication",
    },
    {
        "prompts": {
            "en": "What is the Internet? Answer in one sentence.",
            "zh": "什么是互联网？请用一句话回答。",
            "ja": "インターネットとは何ですか？一文で答えてください。",
            "ko": "인터넷이란 무엇입니까? 한 문장으로 답하세요.",
            "fr": "Qu'est-ce qu'Internet ? Répondez en une phrase.",
            "de": "Was ist das Internet? Antworten Sie in einem Satz.",
            "es": "¿Qué es Internet? Responde en una oración.",
        },
        "expected_keywords": {
            "en": ["network", "connected", "global"],
            "zh": ["网络", "连接", "全球"],
            "ja": ["ネットワーク", "接続", "世界"],
            "ko": ["네트워크", "연결", "세계"],
            "fr": ["réseau", "connecté", "mondial"],
            "de": ["Netzwerk", "verbunden", "global"],
            "es": ["red", "conectado", "global"],
        },
        "description": "What is the Internet",
    },
    {
        "prompts": {
            "en": "How do you say hello? Answer in one sentence.",
            "zh": "你好用什么方式表达？请用一句话回答。",
            "ja": "こんにちははどう言いますか？一文で答えてください。",
            "ko": "안녕하세요는 어떻게 말합니까? 한 문장으로 답하세요.",
            "fr": "Comment dit-on bonjour ? Répondez en une phrase.",
            "de": "Wie sagt man Hallo? Antworten Sie in einem Satz.",
            "es": "¿Cómo se dice hola? Responde en una oración.",
        },
        "expected_keywords": {
            "en": ["hello", "hi", "greeting"],
            "zh": ["你好", "问候", "打招呼"],
            "ja": ["こんにちは", "挨拶", "あいさつ"],
            "ko": ["안녕", "인사"],
            "fr": ["bonjour", "salut"],
            "de": ["hallo", "grüß"],
            "es": ["hola", "saludo"],
        },
        "description": "How do you say hello",
    },
]


class MultilingualEvaluator:
    def __init__(self, languages: Optional[list] = None):
        self.languages = languages or DEFAULT_LANGUAGES

    def evaluate(self, provider, sample: Optional[dict] = None) -> dict:
        """
        Evaluate multilingual capabilities.

        sample (optional):
            prompts: dict[lang_code -> prompt_text]
            expected_keywords: dict[lang_code -> list[str]] (optional)
        """
        if sample is None:
            sample = BUILTIN_SAMPLES[0]

        prompts = sample.get("prompts", {})
        expected_keywords = sample.get("expected_keywords", {})

        lang_scores = {}
        lang_details = {}

        for lang in self.languages:
            prompt = prompts.get(lang)
            if prompt is None:
                continue

            try:
                result = provider.complete(prompt)
                output = result["output"].strip()
            except Exception as e:
                output = ""
                result = {"latency_ms": 0, "prompt_tokens": 0, "completion_tokens": 0}

            # Score the response
            score = self._score_response(output, lang, expected_keywords.get(lang, []))
            lang_scores[lang] = score
            lang_details[lang] = {
                "output": output[:500],
                "score": score,
                "latency_ms": result.get("latency_ms", 0),
            }

        # Compute aggregate
        if lang_scores:
            avg_score = sum(lang_scores.values()) / len(lang_scores)
        else:
            avg_score = 0.0

        # Build per-language score keys
        scores = {"multilingual_avg": avg_score}
        for lang, sc in lang_scores.items():
            scores[f"multilingual_{lang}"] = sc

        # Build a combined output string for display
        output_parts = []
        for lang, detail in lang_details.items():
            output_parts.append(f"[{lang}] {detail['output']}")
        combined_output = "\n\n".join(output_parts)

        # Build a combined input string for display
        input_parts = []
        for lang, prompt in prompts.items():
            if lang in lang_scores:
                input_parts.append(f"[{lang}] {prompt}")
        combined_input = "\n".join(input_parts)

        return {
            "output": combined_output,
            "input_display": combined_input,
            "scores": scores,
            "metadata": {
                "languages_tested": list(lang_scores.keys()),
                "per_language": lang_details,
            },
        }

    def get_builtin_samples(self) -> list:
        return BUILTIN_SAMPLES

    def _score_response(self, output: str, lang: str, expected_keywords: list) -> float:
        """
        Score a response based on:
        1. Non-empty response (basic)
        2. Contains expected keywords (correctness)
        3. Response is in the expected language (language fidelity)
        """
        if not output.strip():
            return 0.0

        score = 0.0

        # Non-empty response: 0.2
        score += 0.2

        # Keyword matching: 0.5
        if expected_keywords:
            output_lower = output.lower()
            matched = sum(1 for kw in expected_keywords if kw.lower() in output_lower)
            keyword_score = matched / len(expected_keywords) if expected_keywords else 0
            score += 0.5 * keyword_score
        else:
            # No keywords to check, give partial credit for non-empty
            score += 0.25

        # Language fidelity: 0.3
        lang_score = self._check_language_fidelity(output, lang)
        score += 0.3 * lang_score

        return min(score, 1.0)

    def _check_language_fidelity(self, text: str, expected_lang: str) -> float:
        """Heuristic check that the response is in the expected language."""
        if not text:
            return 0.0

        if expected_lang == "zh":
            cjk_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            ratio = cjk_chars / max(len(text.replace(" ", "")), 1)
            return 1.0 if ratio > 0.2 else 0.3

        elif expected_lang == "ja":
            jp_chars = sum(1 for c in text if '\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff')
            ratio = jp_chars / max(len(text.replace(" ", "")), 1)
            return 1.0 if ratio > 0.1 else 0.3

        elif expected_lang == "ko":
            kr_chars = sum(1 for c in text if '\uac00' <= c <= '\ud7af')
            ratio = kr_chars / max(len(text.replace(" ", "")), 1)
            return 1.0 if ratio > 0.1 else 0.3

        elif expected_lang in ("fr", "de", "es"):
            # Check for language-specific diacritical marks as a weak signal
            accented = {
                "fr": r'[éèêëàâùûôîïçœæ]',
                "de": r'[äöüßÄÖÜ]',
                "es": r'[áéíóúñ¿¡]',
            }
            pattern = accented.get(expected_lang, "")
            if pattern and re.search(pattern, text):
                return 1.0
            # For short factual answers, Latin script is acceptable
            ascii_ratio = sum(1 for c in text if c.isascii()) / max(len(text), 1)
            return 0.7 if ascii_ratio > 0.8 else 0.5

        elif expected_lang == "en":
            ascii_ratio = sum(1 for c in text if c.isascii()) / max(len(text), 1)
            return 1.0 if ascii_ratio > 0.8 else 0.5

        return 0.5
