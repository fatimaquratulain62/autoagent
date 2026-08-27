"""Tool base class and registry."""
import abc
from typing import Any, ClassVar

from pydantic import BaseModel


class BaseTool(abc.ABC):
    name: ClassVar[str]
    description: ClassVar[str]
    input_schema: ClassVar[type[BaseModel]]

    @abc.abstractmethod
    async def run(self, **kwargs) -> str:
        """Execute the tool and return a string result."""
        ...

    def to_openai_schema(self) -> dict:
        """Convert to OpenAI function-calling format."""
        schema = self.input_schema.model_json_schema()
        # Remove title fields which are noisy
        props = schema.get("properties", {})
        for p in props.values():
            p.pop("title", None)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": props,
                    "required": schema.get("required", []),
                },
            },
        }


# ── Registry ──────────────────────────────────────────────────────────────────

_registry: dict[str, BaseTool] = {}


def register_tool(tool: BaseTool):
    _registry[tool.name] = tool


def get_tool(name: str) -> BaseTool | None:
    return _registry.get(name)


def get_all_tools() -> dict[str, BaseTool]:
    return dict(_registry)


def get_enabled_tools(enabled_names: list[str]) -> list[BaseTool]:
    return [_registry[n] for n in enabled_names if n in _registry]


def get_tool_schemas(enabled_names: list[str]) -> list[dict]:
    return [t.to_openai_schema() for t in get_enabled_tools(enabled_names)]
