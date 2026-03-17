"""
Tool/function calling evaluator.
Tests a model's ability to select the correct tool and provide accurate arguments
given a set of mock tool definitions and a user request.
"""
import json
import re
from typing import Optional


MOCK_TOOLS = [
    {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "parameters": {
            "location": {"type": "string", "description": "City name", "required": True},
            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"], "default": "celsius"},
        },
    },
    {
        "name": "search_web",
        "description": "Search the web for information",
        "parameters": {
            "query": {"type": "string", "description": "Search query", "required": True},
            "num_results": {"type": "integer", "description": "Number of results", "default": 5},
        },
    },
    {
        "name": "send_email",
        "description": "Send an email to a recipient",
        "parameters": {
            "to": {"type": "string", "description": "Recipient email", "required": True},
            "subject": {"type": "string", "description": "Email subject", "required": True},
            "body": {"type": "string", "description": "Email body", "required": True},
        },
    },
    {
        "name": "calculate",
        "description": "Perform a mathematical calculation",
        "parameters": {
            "expression": {"type": "string", "description": "Math expression to evaluate", "required": True},
        },
    },
    {
        "name": "set_reminder",
        "description": "Set a reminder for a specific time",
        "parameters": {
            "message": {"type": "string", "description": "Reminder message", "required": True},
            "time": {"type": "string", "description": "Time in ISO 8601 format", "required": True},
        },
    },
]

BUILTIN_SAMPLES = [
    {
        "user_request": "What's the weather like in Tokyo right now?",
        "expected_tool": "get_weather",
        "expected_args": {"location": "Tokyo"},
    },
    {
        "user_request": "Send an email to alice@example.com with subject 'Meeting' and body 'See you at 3pm'.",
        "expected_tool": "send_email",
        "expected_args": {"to": "alice@example.com", "subject": "Meeting", "body": "See you at 3pm"},
    },
    {
        "user_request": "Calculate 234 * 567 + 89",
        "expected_tool": "calculate",
        "expected_args": {"expression": "234 * 567 + 89"},
    },
    {
        "user_request": "Find information about the latest Mars rover mission.",
        "expected_tool": "search_web",
        "expected_args": {"query": "latest Mars rover mission"},
    },
    {
        "user_request": "帮我查一下北京今天的天气",
        "expected_tool": "get_weather",
        "expected_args": {"location": "北京"},
    },
    {
        "user_request": "帮我计算 156 乘以 23 等于多少",
        "expected_tool": "calculate",
        "expected_args": {"expression": "156 * 23"},
    },
]


class ToolCallingEvaluator:
    def __init__(self, tools: Optional[list] = None):
        self.tools = tools or MOCK_TOOLS

    def evaluate(self, provider, sample: dict) -> dict:
        """
        Evaluate tool calling accuracy.

        sample:
            user_request: str - what the user is asking
            expected_tool: str - name of the correct tool
            expected_args: dict - expected argument key-value pairs
            tools: list (optional) - override default tool definitions
        """
        user_request = sample.get("user_request", "")
        expected_tool = sample.get("expected_tool", "")
        expected_args = sample.get("expected_args", {})
        tools = sample.get("tools", self.tools)

        tools_description = self._format_tools(tools)

        prompt = (
            f"You have access to the following tools:\n\n"
            f"{tools_description}\n\n"
            f"User request: {user_request}\n\n"
            f"Respond with a JSON object indicating which tool to call and with what arguments. "
            f"Format: {{\"tool\": \"tool_name\", \"arguments\": {{...}}}}\n"
            f"Respond with ONLY the JSON, no other text."
        )

        result = provider.complete(prompt)
        output = result["output"].strip()

        # Parse the model's tool call
        parsed_call = self._parse_tool_call(output)

        # Score tool selection
        predicted_tool = parsed_call.get("tool", "")
        tool_correct = predicted_tool.lower() == expected_tool.lower()

        # Score argument accuracy
        predicted_args = parsed_call.get("arguments", {})
        arg_accuracy = self._compute_arg_accuracy(predicted_args, expected_args)

        return {
            "output": output,
            "scores": {
                "tool_selection_accuracy": 1.0 if tool_correct else 0.0,
                "argument_accuracy": arg_accuracy,
            },
            "metadata": {
                "predicted_tool": predicted_tool,
                "expected_tool": expected_tool,
                "predicted_args": predicted_args,
                "expected_args": expected_args,
                "tool_correct": tool_correct,
            },
            **{k: v for k, v in result.items() if k != "output"},
        }

    def get_builtin_samples(self) -> list:
        return BUILTIN_SAMPLES

    def _format_tools(self, tools: list) -> str:
        """Format tool definitions for the prompt."""
        parts = []
        for tool in tools:
            params_lines = []
            for pname, pinfo in tool.get("parameters", {}).items():
                req = " (required)" if pinfo.get("required") else ""
                desc = pinfo.get("description", "")
                ptype = pinfo.get("type", "string")
                params_lines.append(f"    - {pname} ({ptype}){req}: {desc}")
            params_text = "\n".join(params_lines) if params_lines else "    (no parameters)"
            parts.append(
                f"Tool: {tool['name']}\n"
                f"  Description: {tool['description']}\n"
                f"  Parameters:\n{params_text}"
            )
        return "\n\n".join(parts)

    def _parse_tool_call(self, text: str) -> dict:
        """Parse a tool call JSON from the model's output."""
        # Try direct JSON parse
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "tool" in data:
                return data
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        code_match = re.search(r'```(?:json)?\s*\n?(.*?)```', text, re.DOTALL)
        if code_match:
            try:
                data = json.loads(code_match.group(1).strip())
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass

        # Try to find JSON object boundaries
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            try:
                data = json.loads(text[start:end + 1])
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass

        return {"tool": "", "arguments": {}}

    def _compute_arg_accuracy(self, predicted: dict, expected: dict) -> float:
        """Compute accuracy of predicted arguments vs expected."""
        if not expected:
            return 1.0 if not predicted else 0.5

        matched = 0
        total = len(expected)

        for key, exp_value in expected.items():
            pred_value = predicted.get(key)
            if pred_value is None:
                continue

            # Flexible string comparison
            exp_str = str(exp_value).lower().strip()
            pred_str = str(pred_value).lower().strip()

            if exp_str == pred_str:
                matched += 1
            elif exp_str in pred_str or pred_str in exp_str:
                matched += 0.5

        return matched / total if total > 0 else 0.0
