from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTool(ABC):
    """
    Abstract base class for all tools in the Q-ACE framework.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A description of what the tool does, used by the LLM."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Executes the tool with the given arguments."""
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """Returns metadata about the tool for LLM consumption."""
        return {
            "name": self.name,
            "description": self.description,
        }
