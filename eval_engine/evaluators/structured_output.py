"""
Structured output evaluator.
Tests a model's ability to produce valid JSON that conforms to a given schema.
"""
import json
import re
from typing import Optional


BUILTIN_SAMPLES = [
    {
        "instruction": "Generate a JSON object representing a person with fields: name (string), age (integer), email (string).",
        "schema": {
            "type": "object",
            "required": ["name", "age", "email"],
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "email": {"type": "string"},
            },
        },
    },
    {
        "instruction": "Generate a JSON array of exactly 3 objects, each with 'city' (string) and 'population' (number) fields.",
        "schema": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {
                "type": "object",
                "required": ["city", "population"],
                "properties": {
                    "city": {"type": "string"},
                    "population": {"type": "number"},
                },
            },
        },
    },
    {
        "instruction": "Generate a JSON object with: 'title' (string), 'tags' (array of strings, at least 2), 'metadata' (object with 'author' string and 'year' integer).",
        "schema": {
            "type": "object",
            "required": ["title", "tags", "metadata"],
            "properties": {
                "title": {"type": "string"},
                "tags": {"type": "array", "minItems": 2, "items": {"type": "string"}},
                "metadata": {
                    "type": "object",
                    "required": ["author", "year"],
                    "properties": {
                        "author": {"type": "string"},
                        "year": {"type": "integer"},
                    },
                },
            },
        },
    },
    {
        "instruction": "生成一个学生信息的JSON对象，包含姓名(name)、年龄(age)和成绩(score)",
        "schema": {
            "type": "object",
            "required": ["name", "age", "score"],
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "score": {"type": "number"},
            },
        },
    },
    {
        "instruction": "生成一个包含3道菜品的菜单JSON数组，每道菜有名称(name)和价格(price)",
        "schema": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {
                "type": "object",
                "required": ["name", "price"],
                "properties": {
                    "name": {"type": "string"},
                    "price": {"type": "number"},
                },
            },
        },
    },
    {
        "instruction": "生成一个城市天气JSON，包含城市名(city)、温度(temperature)、天气状况(condition)和湿度(humidity)",
        "schema": {
            "type": "object",
            "required": ["city", "temperature", "condition", "humidity"],
            "properties": {
                "city": {"type": "string"},
                "temperature": {"type": "number"},
                "condition": {"type": "string"},
                "humidity": {"type": "number"},
            },
        },
    },
]


class StructuredOutputEvaluator:
    def __init__(self):
        pass

    def evaluate(self, provider, sample: dict) -> dict:
        """
        Evaluate structured output generation.

        sample:
            instruction: str - what to generate
            schema: dict - JSON schema the output must conform to
        """
        instruction = sample.get("instruction", "")
        schema = sample.get("schema", {})

        prompt = (
            f"{instruction}\n\n"
            f"Respond with ONLY valid JSON, no markdown formatting, no explanation."
        )

        result = provider.complete(prompt)
        output = result["output"].strip()

        # Try to parse JSON from the output
        parsed, json_valid = self._extract_and_parse_json(output)

        # Validate against schema
        schema_compliant = False
        validation_errors = []
        if json_valid and schema:
            schema_compliant, validation_errors = self._validate_schema(parsed, schema)

        return {
            "output": output,
            "scores": {
                "json_valid": 1.0 if json_valid else 0.0,
                "schema_compliant": 1.0 if schema_compliant else 0.0,
            },
            "metadata": {
                "parsed_json": parsed if json_valid else None,
                "validation_errors": validation_errors,
            },
            **{k: v for k, v in result.items() if k != "output"},
        }

    def get_builtin_samples(self) -> list:
        return BUILTIN_SAMPLES

    def _extract_and_parse_json(self, text: str) -> tuple:
        """Try to parse JSON from text, handling common wrapper patterns."""
        # Try direct parse
        try:
            return json.loads(text), True
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        code_match = re.search(r'```(?:json)?\s*\n?(.*?)```', text, re.DOTALL)
        if code_match:
            try:
                return json.loads(code_match.group(1).strip()), True
            except json.JSONDecodeError:
                pass

        # Try to find JSON object or array boundaries
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start_idx = text.find(start_char)
            end_idx = text.rfind(end_char)
            if start_idx != -1 and end_idx > start_idx:
                candidate = text[start_idx:end_idx + 1]
                try:
                    return json.loads(candidate), True
                except json.JSONDecodeError:
                    pass

        return None, False

    def _validate_schema(self, data, schema: dict) -> tuple:
        """
        Lightweight JSON schema validation without external dependencies.
        Returns (is_valid, list_of_errors).
        """
        errors = []
        self._validate_node(data, schema, "", errors)
        return len(errors) == 0, errors

    def _validate_node(self, data, schema: dict, path: str, errors: list):
        """Recursively validate a data node against a schema node."""
        expected_type = schema.get("type")

        # Type checking
        if expected_type:
            if not self._check_type(data, expected_type):
                errors.append(f"{path or 'root'}: expected type '{expected_type}', got '{type(data).__name__}'")
                return

        if expected_type == "object" and isinstance(data, dict):
            # Check required fields
            required = schema.get("required", [])
            for field in required:
                if field not in data:
                    errors.append(f"{path}.{field}: required field missing")

            # Validate properties
            properties = schema.get("properties", {})
            for key, prop_schema in properties.items():
                if key in data:
                    self._validate_node(data[key], prop_schema, f"{path}.{key}", errors)

        elif expected_type == "array" and isinstance(data, list):
            # Check min/max items
            min_items = schema.get("minItems")
            max_items = schema.get("maxItems")
            if min_items is not None and len(data) < min_items:
                errors.append(f"{path}: expected at least {min_items} items, got {len(data)}")
            if max_items is not None and len(data) > max_items:
                errors.append(f"{path}: expected at most {max_items} items, got {len(data)}")

            # Validate each item
            items_schema = schema.get("items")
            if items_schema:
                for i, item in enumerate(data):
                    self._validate_node(item, items_schema, f"{path}[{i}]", errors)

    def _check_type(self, data, expected_type: str) -> bool:
        """Check if data matches the expected JSON schema type."""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None),
        }
        expected = type_map.get(expected_type)
        if expected is None:
            return True  # Unknown type, skip check
        if expected_type == "integer" and isinstance(data, bool):
            return False  # bool is subclass of int in Python
        return isinstance(data, expected)
