import ollama
from typing import List, Dict, Any, Optional
from providers.base_provider import BaseLLMProvider

class OllamaProvider(BaseLLMProvider):
    """
    LLM Provider using local Ollama.
    """
    def __init__(self, model_name: str = "llama3", base_url: Optional[str] = None):
        self.model_name = model_name
        self.base_url = base_url

    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generates a response using Ollama's AsyncClient.
        """
        client = ollama.AsyncClient(host=getattr(self, 'base_url', None))
        response = await client.chat(
            model=self.model_name,
            messages=messages,
            # tools=tools
        )
        
        return {
            "content": response["message"]["content"],
            "tool_calls": response["message"].get("tool_calls", [])
        }
