"""
Config and Ollama management endpoints.
Routes: /api/config, /api/ollama/*
"""

import os
import json
import sqlite3
import subprocess

import requests
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any

from routers.dependencies import get_current_user, _get_user_config, global_config

router = APIRouter()

# Track the locally-spawned ollama process
ollama_process = None


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ConfigUpdate(BaseModel):
    provider: str
    gemini_model: Optional[str] = None
    ollama_model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    json_config: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/api/config")
def get_config(request: Request):
    """Returns the current user configuration from DB, falling back to global."""
    return _get_user_config(request)


@router.post("/api/config")
async def update_config(config: ConfigUpdate, request: Request):
    """Updates the user configuration in the DB."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user_id = user["user_id"]
    data = config.dict(exclude_unset=True)

    conn = sqlite3.connect("data/q-ace.db")
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM user_settings WHERE user_id = ?", (user_id,))
    exists = cursor.fetchone()

    if "json_config" in data and isinstance(data["json_config"], dict):
        data["json_config"] = json.dumps(data["json_config"])

    if exists:
        keys = ", ".join([f"{k} = ?" for k in data.keys()])
        cursor.execute(f"UPDATE user_settings SET {keys} WHERE user_id = ?", (*data.values(), user_id))
    else:
        full_data = {**global_config, "user_id": user_id, **data}
        table_keys = ["user_id", "provider", "gemini_model", "ollama_model", "api_key", "base_url", "json_config"]
        item_data = {k: full_data.get(k) for k in table_keys}

        cols = ", ".join(item_data.keys())
        placeholders = ", ".join(["?" for _ in item_data])
        cursor.execute(f"INSERT INTO user_settings ({cols}) VALUES ({placeholders})", tuple(item_data.values()))

    conn.commit()
    conn.close()

    return get_config(request)


@router.get("/api/ollama/status")
def get_ollama_status(request: Request):
    """Checks if Ollama server is running using the user's configured base URL."""
    cfg = _get_user_config(request)
    base_url = cfg.get("base_url", global_config["base_url"])
    is_running = False
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=2)
        if response.status_code == 200:
            is_running = True
    except Exception:
        is_running = False

    return {"running": is_running}


@router.post("/api/ollama/manage")
async def manage_ollama(action: Dict[str, str]):
    """Starts or stops the Ollama server."""
    global ollama_process
    act = action.get("action")

    if act == "start":
        if ollama_process is None or ollama_process.poll() is not None:
            try:
                ollama_process = subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
                )
                return {"status": "starting"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to start Ollama: {str(e)}")
        return {"status": "already_running"}

    elif act == "stop":
        stopped = False
        if ollama_process:
            ollama_process.terminate()
            ollama_process = None
            stopped = True

        if os.name == "nt":
            try:
                subprocess.run(["taskkill", "/f", "/im", "ollama.exe"], capture_output=True)
                stopped = True
            except Exception:
                pass

        return {"status": "stopped" if stopped else "no_process_found"}

    return {"status": "invalid_action"}
