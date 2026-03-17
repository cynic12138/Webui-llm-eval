from typing import Callable, Any
import inspect


class ToolDefinition:
    def __init__(
        self,
        name: str,
        description: str,
        category: str,
        parameters: dict[str, Any],
        handler: Callable,
        requires_confirmation: bool = False,
    ):
        self.name = name
        self.description = description
        self.category = category
        self.parameters = parameters
        self.handler = handler
        self.requires_confirmation = requires_confirmation


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        category: str,
        parameters: dict[str, Any],
        requires_confirmation: bool = False,
    ):
        def decorator(func: Callable):
            self._tools[name] = ToolDefinition(
                name=name,
                description=description,
                category=category,
                parameters=parameters,
                handler=func,
                requires_confirmation=requires_confirmation,
            )
            return func
        return decorator

    def get_tool(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    async def execute(self, name: str, **kwargs) -> Any:
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")
        if inspect.iscoroutinefunction(tool.handler):
            return await tool.handler(**kwargs)
        return tool.handler(**kwargs)

    def list_tools(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "parameters": t.parameters,
                "requires_confirmation": t.requires_confirmation,
            }
            for t in self._tools.values()
        ]

    def to_openai_tools(self) -> list[dict]:
        tools = []
        for t in self._tools.values():
            tools.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            })
        return tools


registry = ToolRegistry()
