from core.base_tool import BaseTool
from typing import Any

class PlaceholderTool(BaseTool):
    """
    A placeholder tool that returns a success message.
    """
    @property
    def name(self) -> str:
        return "placeholder_tool"

    @property
    def description(self) -> str:
        return "A simple tool that returns a success message to verify the tool execution flow."

    async def execute(self, **kwargs) -> Any:
        return {"status": "success", "message": "Tool Executed Successfully"}
