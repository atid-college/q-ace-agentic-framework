"""
Shared state, helpers, and initialized objects used across all router modules.
All routers import from here instead of from main.py.
"""

import os
import asyncio
import json
import sqlite3
from typing import Dict, Any, List, Optional

from fastapi import Request, HTTPException


from core.tool_registry import ToolRegistry
from tools.placeholder_tool import PlaceholderTool
from tools.api_tool import APITool
from tools.sqlite_tool import SQLiteTool
from tools.browser_tool import BrowserTool
from tools.mobile_tool import MobileTool
from tools.spec_analyzer_tool import SpecAnalyzerTool

from handlers.sqlite_handler import SQLiteHandler
from handlers.api_handler import APIHandler
from handlers.spec_analyzer_handler import SpecAnalyzerHandler
from handlers.placeholder_handler import PlaceholderHandler
from handlers.auth_handler import AuthHandler
from handlers.browser_handler import BrowserHandler
from handlers.mobile_handler import MobileHandler

from core.auth_utils import verify_access_token

# ---------------------------------------------------------------------------
# Global LLM config (falls back to env vars)
# ---------------------------------------------------------------------------
global_config: Dict[str, Any] = {
    "provider": os.environ.get("Q_ACE_PROVIDER", "gemini"),
    "gemini_model": os.environ.get("Q_ACE_GEMINI_MODEL", "gemini-2.5-flash-lite"),
    "ollama_model": os.environ.get("Q_ACE_OLLAMA_MODEL", "gemma3:1b"),
    "api_key": "",  # Hidden from UI, LLMClient will fallback to os.environ if empty
    "base_url": "http://localhost:11434",
}
global_config["model"] = (
    global_config["gemini_model"]
    if global_config["provider"] == "gemini"
    else global_config["ollama_model"]
)

# ---------------------------------------------------------------------------
# Async queues / in-memory task tracking
# ---------------------------------------------------------------------------
db_update_queue: asyncio.Queue = asyncio.Queue()

active_browser_tasks: Dict[int, Dict[str, Any]] = {}  # user_id -> task info
active_mobile_tasks: Dict[int, Dict[str, Any]] = {}   # user_id -> task info

# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------
registry = ToolRegistry()
registry.register_tool(PlaceholderTool())
registry.register_tool(APITool())
registry.register_tool(SQLiteTool())
registry.register_tool(BrowserTool())
registry.register_tool(MobileTool())
registry.register_tool(SpecAnalyzerTool())

# ---------------------------------------------------------------------------
# Handler map
# ---------------------------------------------------------------------------
handlers: Dict[str, Any] = {
    "sqlite": SQLiteHandler(),
    "spec_analyzer": SpecAnalyzerHandler(),
    "browser_agent": BrowserHandler(),
    "mobile_agent": MobileHandler(),
    "api": APIHandler(),
    "jenkins": PlaceholderHandler("jenkins", "Jenkins Agent", "wrench", "Integration with Jenkins pipelines.", "Run test suite example on Linux environment"),
    "github_actions": PlaceholderHandler("github_actions", "GitHub Actions", "play-circle", "Automation with GitHub Actions workflows.", "Run test suite example on Linux environment"),
    "postman": PlaceholderHandler("postman", "Postman", "send", "API Testing with Postman collections.", "Run collection named Sanity"),
    "github": PlaceholderHandler("github", "GitHub", "github", "Repository management and source control.", "Upload sanity-bank-system document to main branch"),
    "jira": PlaceholderHandler("jira", "Jira", "trello", "Project management and issue tracking.", "Open a bug under project ABC with details..."),
    "qase": PlaceholderHandler("qase", "Qase", "shield-check", "Test management platform integration.", "Open a bug under project ABC with details..."),
    "slack": PlaceholderHandler("slack", "Slack", "message-square", "Communication and notifications with Slack.", "Post a message to #qa-alerts: Deploy successful"),
    "auth": AuthHandler(),
}

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Extract and verify the JWT from the cookie or Authorization header."""
    token = request.cookies.get("q_ace_token")
    
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
    if not token:
        return None
        
    user = verify_access_token(token)
    return user





def _get_user_config(request: Request) -> Dict[str, Any]:
    """Return the current user's config from DB, falling back to global_config."""
    user = get_current_user(request)
    if not user:
        return global_config

    user_id = user["user_id"]
    conn = sqlite3.connect("data/q-ace.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        cfg = dict(row)
        cfg["model"] = cfg["gemini_model"] if cfg["provider"] == "gemini" else cfg["ollama_model"]
        if "json_config" in cfg and cfg["json_config"]:
            try:
                cfg["json_config"] = json.loads(cfg["json_config"])
            except Exception:
                pass
        return cfg
    return global_config
