from typing import Dict, Any, List, Optional
from handlers.base_handler import BaseHandler

class PlaceholderHandler(BaseHandler):
    """
    A generic UI Handler for placeholder tools that show a "Coming Soon" interface.
    """
    
    def __init__(self, tool_id: str, tool_name: str, icon: str, description: str, example_prompt: str):
        self._tool_id = tool_id
        self._tool_name = tool_name
        self._icon = icon
        self._description = description
        self._example_prompt = example_prompt

    @property
    def tool_id(self) -> str:
        return self._tool_id

    @property
    def tool_name(self) -> str:
        return self._tool_name

    @property
    def icon(self) -> str:
        return self._icon

    def get_ui_definition(self) -> Dict[str, Any]:
        return {
            "title": self.tool_name,
            "description": self._description,
            "is_placeholder": True,
            "components": [
                {
                     "type": "textarea",
                     "id": "prompt",
                     "label": "Agent Instruction",
                     "placeholder": f"e.g., '{self._example_prompt}'"
                 },
                 {
                     "type": "button",
                     "id": "execute_btn",
                     "label": "Execute (Coming Soon)",
                     "action": "placeholder_execute",
                     "style": "bg-slate-400 cursor-not-allowed"
                 }
            ]
        }
        
    async def handle_action(self, action: str, data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handles actions for placeholder tools.
        """
        if action == "placeholder_execute":
            return {
                "status": "info", 
                "message": f"The {self.tool_name} integration is currently a placeholder. Full implementation is coming soon!"
            }

        return {"status": "error", "message": f"Unknown action: {action}"}
