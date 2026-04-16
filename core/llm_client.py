import os
from typing import Dict, Any, List, Optional
from providers.base_provider import BaseLLMProvider
from providers.gemini_provider import GeminiProvider
from providers.ollama_provider import OllamaProvider

class LLMClient:
    """
    Unified LLM Client to dynamically switch between providers 
    based on runtime settings.
    """
    
    @staticmethod
    def get_provider(settings: Dict[str, Any]) -> BaseLLMProvider:
        provider_type = settings.get("provider", "gemini").lower()
        model_name = settings.get("model", "gemini-2.5-flash")
        api_key = settings.get("api_key", "")
        base_url = settings.get("base_url", "http://localhost:11434")

        if provider_type == "gemini":
            if not api_key:
                # Fallback to env if not provided in settings
                api_key = os.environ.get("GOOGLE_API_KEY", "")
            return GeminiProvider(model_name=model_name, api_key=api_key)
        
        elif provider_type == "ollama":
            return OllamaProvider(model_name=model_name, base_url=base_url)
        
        else:
            raise ValueError(f"Unsupported LLM provider: {provider_type}")

    @staticmethod
    async def get_ai_response(prompt: str, settings: Dict[str, Any]) -> str:
        """
        One-shot utility to get a response from the configured LLM.
        """
        provider = LLMClient.get_provider(settings)
        messages = [{"role": "user", "content": prompt}]
        response = await provider.generate_response(messages)
        return response["content"]
