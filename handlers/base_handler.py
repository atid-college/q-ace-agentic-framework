from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseHandler(ABC):
    """
    Standard interface for all tool handlers in the Q-ACE framework.
    """

    @property
    @abstractmethod
    def tool_id(self) -> str:
        """Unique identifier for the tool."""
        pass

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Display name for the tool sidebar."""
        pass

    @property
    @abstractmethod
    def icon(self) -> str:
        """Lucide icon name or SVG path for the sidebar."""
        pass

    @abstractmethod
    def get_ui_definition(self) -> Dict[str, Any]:
        """
        Returns a definition of the tool's interface that the frontend can render.
        Includes fields, buttons, and layout.
        """
        pass

    @abstractmethod
    async def handle_action(self, action: str, data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handles an action sent from the frontend for this specific tool.
        'context' may include active LLM provider, configurations, etc.
        """
        pass
