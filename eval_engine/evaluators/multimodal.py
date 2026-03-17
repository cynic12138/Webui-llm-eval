"""
Multimodal (image + text) evaluator.
Tests vision capabilities if the provider supports them,
otherwise falls back to text-only evaluation.
"""
import re
import base64
import os
from typing import Optional


BUILTIN_TEXT_SAMPLES = [
    {
        "text": "Describe what a stop sign looks like in detail.",
        "expected_keywords": ["red", "octagon", "stop", "white"],
        "description": "Stop sign description (text-only fallback)",
    },
    {
        "text": "What are the typical elements in a bar chart? Describe them.",
        "expected_keywords": ["axis", "bar", "label"],
        "description": "Bar chart description (text-only fallback)",
    },
    {
        "text": "请描述一个典型的红绿灯交通信号灯的外观和功能。",
        "question": "交通信号灯有哪些颜色？每种颜色代表什么含义？",
        "expected_keywords": ["红", "绿", "黄", "停", "行"],
    },
    {
        "text": "请描述一张典型的世界地图的内容。",
        "question": "世界地图上通常用什么颜色表示海洋和陆地？",
        "expected_keywords": ["蓝", "海洋", "陆地", "大陆"],
    },
]

BUILTIN_VISION_SAMPLES = [
    {
        "image_description": "A red stop sign at an intersection",
        "question": "What does this sign say and what should a driver do?",
        "expected_keywords": ["stop", "halt", "wait"],
        "description": "Stop sign recognition",
    },
    {
        "image_description": "A bar chart showing sales data for Q1-Q4",
        "question": "What type of chart is this and what does it show?",
        "expected_keywords": ["bar", "chart", "sales"],
        "description": "Chart interpretation",
    },
]


class MultimodalEvaluator:
    def __init__(self):
        pass

    def evaluate(self, provider, sample: dict) -> dict:
        """
        Evaluate multimodal (vision + text) or text-only capabilities.

        sample:
            image_path: str (optional) - path to an image file
            image_base64: str (optional) - base64-encoded image
            question: str - question about the image (or text prompt)
            expected_keywords: list[str] (optional) - keywords expected in the answer
            text: str (optional) - text-only fallback prompt
        """
        has_image = bool(sample.get("image_path") or sample.get("image_base64"))
        supports_vision = self._check_vision_support(provider)

        if has_image and supports_vision:
            return self._evaluate_vision(provider, sample)
        else:
            return self._evaluate_text(provider, sample)

    def _evaluate_vision(self, provider, sample: dict) -> dict:
        """Evaluate with image input."""
        image_data = sample.get("image_base64", "")
        image_path = sample.get("image_path", "")
        question = sample.get("question", "Describe this image in detail.")
        expected_keywords = sample.get("expected_keywords", [])

        # Load image from path if needed
        if not image_data and image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

        # Build prompt with image reference
        # Most vision APIs accept base64 images via special formatting;
        # here we pass it as a kwarg to provider.complete
        prompt = f"Look at the provided image and answer: {question}"

        try:
            result = provider.complete(prompt, image_base64=image_data)
        except TypeError:
            # Provider does not accept image_base64 kwarg, fall back
            return self._evaluate_text(provider, sample)

        output = result["output"].strip()

        # Score based on expected keywords
        keyword_score = self._keyword_score(output, expected_keywords)

        # Basic quality: non-empty and reasonably long
        quality_score = min(len(output.split()) / 10.0, 1.0) if output else 0.0

        vision_accuracy = (keyword_score * 0.7 + quality_score * 0.3) if expected_keywords else quality_score

        return {
            "output": output,
            "scores": {
                "vision_accuracy": vision_accuracy,
            },
            "metadata": {
                "mode": "vision",
                "keyword_score": keyword_score,
                "quality_score": quality_score,
                "expected_keywords": expected_keywords,
            },
            **{k: v for k, v in result.items() if k != "output"},
        }

    def _evaluate_text(self, provider, sample: dict) -> dict:
        """Evaluate with text-only input (fallback)."""
        # Use text prompt or build one from the question
        text = sample.get("text", "")
        if not text:
            question = sample.get("question", "")
            image_desc = sample.get("image_description", "")
            if image_desc:
                text = f"Imagine you are looking at: {image_desc}\n\n{question}"
            else:
                text = question

        expected_keywords = sample.get("expected_keywords", [])

        if not text:
            return {
                "output": "",
                "scores": {"text_accuracy": 0.0},
                "metadata": {"mode": "text", "error": "No prompt provided"},
            }

        result = provider.complete(text)
        output = result["output"].strip()

        keyword_score = self._keyword_score(output, expected_keywords)
        quality_score = min(len(output.split()) / 10.0, 1.0) if output else 0.0
        text_accuracy = (keyword_score * 0.7 + quality_score * 0.3) if expected_keywords else quality_score

        return {
            "output": output,
            "scores": {
                "text_accuracy": text_accuracy,
            },
            "metadata": {
                "mode": "text",
                "vision_supported": False,
                "keyword_score": keyword_score,
                "quality_score": quality_score,
            },
            **{k: v for k, v in result.items() if k != "output"},
        }

    def _check_vision_support(self, provider) -> bool:
        """Check whether the provider supports vision/image input."""
        # Check for explicit attribute
        if hasattr(provider, "supports_vision"):
            return bool(provider.supports_vision)

        # Check model name for known vision models
        model_name = getattr(provider, "model", "") or getattr(provider, "model_name", "")
        model_lower = model_name.lower()
        vision_indicators = ["vision", "gpt-4o", "gpt-4-turbo", "claude-3", "gemini"]
        return any(indicator in model_lower for indicator in vision_indicators)

    def _keyword_score(self, output: str, keywords: list) -> float:
        """Score based on presence of expected keywords."""
        if not keywords:
            return 1.0
        output_lower = output.lower()
        matched = sum(1 for kw in keywords if kw.lower() in output_lower)
        return matched / len(keywords)

    def get_builtin_samples(self, vision: bool = False) -> list:
        return BUILTIN_VISION_SAMPLES if vision else BUILTIN_TEXT_SAMPLES
