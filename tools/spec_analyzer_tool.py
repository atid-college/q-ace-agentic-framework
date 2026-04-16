from typing import Any, Dict, List, Optional
from core.base_tool import BaseTool
from handlers.spec_analyzer_handler import SpecAnalyzerHandler

class SpecAnalyzerTool(BaseTool):
    """
    A tool to generate test cases and analyze technical specifications.
    """
    
    def __init__(self):
        self.handler = SpecAnalyzerHandler()

    @property
    def name(self) -> str:
        return "spec_analyzer_tool"

    @property
    def description(self) -> str:
        return (
            "An agentic tool to analyze specifications (PDF, URL, MD) and generate test cases.\n"
            "Arguments required:\n"
            "- 'custom_path': A custom path or URL to the specification document (e.g. 'https://example.com/spec', 'C:/docs/spec.pdf').\n"
            "- 'spec_file': (Optional) An existing spec filename in the system.\n"
            "- 'category': (Optional) The category of tests to generate (e.g. 'functionality', 'security', 'performance'). Defaults to 'functionality'.\n"
            "- 'techniques': (Optional) A list of specific testing techniques (e.g. ['edge_cases', 'bva', 'ep'])."
        )

    async def execute(self, **kwargs) -> Any:
        spec_file = kwargs.get("spec_file")
        custom_path = kwargs.get("custom_path")
        category = kwargs.get("category", "functionality")
        techniques = kwargs.get("techniques", [])
        provider = kwargs.get("_provider")
        
        if not spec_file and not custom_path:
            return {"status": "error", "message": "Either 'spec_file' or 'custom_path' must be provided."}
            
        data = {
            "custom_path": custom_path,
            "spec_file": spec_file if spec_file else "custom",
            "category": category,
            "techniques": techniques
        }
        
        context = {"provider": provider} if provider else {}
        
        return await self.handler.handle_action("analyze_spec", data, context)
