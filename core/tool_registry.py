from typing import Dict, List, Any, Type
from core.base_tool import BaseTool

class ToolRegistry:
    """
    Registry for managing tools available to the Agent.
    """
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register_tool(self, tool: BaseTool):
        """Registers a tool instance."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool:
        """Returns a tool by name."""
        return self._tools.get(name)

    def get_all_tools(self) -> List[BaseTool]:
        """Returns all registered tool instances."""
        return list(self._tools.values())

    def get_tools_metadata(self) -> List[Dict[str, Any]]:
        """Returns metadata for all tools in a format LLMs can understand."""
        return [tool.get_metadata() for tool in self._tools.values()]
