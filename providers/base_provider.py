from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    """

    @abstractmethod
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generates a response from the LLM.
        
        Args:
            messages: List of chat messages.
            tools: Optional list of tool definitions.
            
        Returns:
            A dictionary containing the response text and any tool calls.
        """
        pass
