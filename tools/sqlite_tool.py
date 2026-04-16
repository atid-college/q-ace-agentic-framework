from typing import Any, Dict, Optional
from core.base_tool import BaseTool
from handlers.sqlite_handler import SQLiteHandler

class SQLiteTool(BaseTool):
    """
    A tool to query and interact with SQLite databases using natural language.
    """
    
    def __init__(self):
        self.handler = SQLiteHandler()

    @property
    def name(self) -> str:
        return "sqlite_tool"

    @property
    def description(self) -> str:
        return (
            "An agentic tool to query SQLite databases using natural language.\n"
            "Arguments required:\n"
            "- 'prompt': The natural language question or request about the data.\n"
            "- 'sample_db': (Optional) The name of a sample database to use (e.g. 'chinook.db', 'northwind.db', 'qa_test.db'). If not provided, it defaults to querying the active or most relevant DB.\n"
            "- 'db_path': (Optional) Absolute path to a custom SQLite database."
        )

    async def execute(self, **kwargs) -> Any:
        prompt = kwargs.get("prompt")
        sample_db = kwargs.get("sample_db", "chinook.db") # Defaulting to chinook if none provided
        db_path = kwargs.get("db_path", "")
        provider = kwargs.get("_provider") # Injected by Orchestrator
        queue = kwargs.get("_queue")       # Injected by Orchestrator
        step_id = kwargs.get("_step_id")   # Injected by Orchestrator
        
        if not prompt:
            return {"status": "error", "message": "'prompt' is strictly required."}
            
        data = {
            "prompt": prompt,
            "sample_db": sample_db,
            "db_path": db_path
        }
        
        context = {
            "provider": provider,
            "queue": queue,
            "step_id": step_id
        }
        
        return await self.handler.handle_action("text_to_sql", data, context)
