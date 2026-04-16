"""
Mobile Agent endpoints: history, stats, config, SSE run.
Routes: /api/mobile-agent/*
"""

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from routers.dependencies import get_current_user, global_config, active_mobile_tasks
from handlers.mobile_handler import run_mobile_agent_stream
from core.auth_utils import verify_access_token

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class MobileAgentRunRequest(BaseModel):
    task: str
    token: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    appium_config: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/api/mobile-agent/history")
async def get_mobile_history(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    conn = sqlite3.connect("data/q-ace.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM mobile_agent_history WHERE user_id = ? ORDER BY timestamp DESC",
        (user["user_id"],),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    for row in rows:
        try:
            row["logs"] = json.loads(row["logs"])
        except Exception:
            row["logs"] = []
        try:
            row["history_json"] = json.loads(row["history_json"]) if row.get("history_json") else None
        except Exception:
            row["history_json"] = None
    return rows


@router.post("/api/mobile-agent/history")
async def save_mobile_history(data: Dict[str, Any], request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    conn = sqlite3.connect("data/q-ace.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO mobile_agent_history (user_id, prompt, logs, history_json, result, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user["user_id"],
            data.get("prompt"),
            json.dumps(data.get("logs", [])),
            json.dumps(data.get("history_json", {})),
            data.get("result"),
            data.get("status", "success"),
        ),
    )

    conn.commit()
    conn.close()
    return {"status": "success"}


@router.delete("/api/mobile-agent/history/clear")
async def clear_mobile_history(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    conn = sqlite3.connect("data/q-ace.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM mobile_agent_history WHERE user_id=?", (user["user_id"],))
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.delete("/api/mobile-agent/history/{history_id}")
async def delete_mobile_history(history_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    conn = sqlite3.connect("data/q-ace.db")
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM mobile_agent_history WHERE id=? AND user_id=?",
        (history_id, user["user_id"]),
    )
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.get("/api/mobile-agent/stats")
async def get_mobile_stats(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    conn = sqlite3.connect("data/q-ace.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT result, timestamp FROM mobile_agent_history WHERE user_id = ? ORDER BY timestamp DESC",
        (user["user_id"],),
    )
    rows = cursor.fetchall()
    conn.close()

    total = len(rows)
    failed = sum(
        1 for r in rows
        if r["result"] and (
            r["result"].startswith("Failed:")
            or r["result"].startswith("Exception:")
            or r["result"] == "Task cancelled by user."
        )
    )
    success = total - failed
    rate = round((success / total) * 100) if total > 0 else 0

    today = datetime.utcnow().date()
    daily_map = {str(today - timedelta(days=i)): 0 for i in range(6, -1, -1)}
    for r in rows:
        try:
            day = r["timestamp"][:10]
            if day in daily_map:
                daily_map[day] += 1
        except Exception:
            pass
    daily = [{"day": d, "count": c} for d, c in daily_map.items()]

    return {"total": total, "success": success, "failed": failed, "rate": rate, "daily": daily}


@router.get("/api/mobile-agent/config")
async def get_mobile_agent_config(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    conn = sqlite3.connect("data/q-ace.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    row = cursor.execute(
        "SELECT appium_config FROM mobile_agent_config WHERE user_id = ?",
        (user["user_id"],),
    ).fetchone()
    conn.close()

    if row:
        return json.loads(row["appium_config"])
    return {
        "serverUrl": "http://localhost:4723",
        "platformName": "Android",
        "udid": "",
        "appPackage": "",
        "appActivity": "",
    }


@router.post("/api/mobile-agent/config")
async def save_mobile_agent_config(config: dict, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    conn = sqlite3.connect("data/q-ace.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO mobile_agent_config (user_id, appium_config)
        VALUES (?, ?)
        """,
        (user["user_id"], json.dumps(config)),
    )
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.get("/api/mobile-agent/active-task")
async def get_active_mobile_task(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    task_info = active_mobile_tasks.get(user["user_id"])
    if task_info:
        return {"active": True, "task": task_info["task"]}
    return {"active": False}


@router.post("/api/mobile-agent/stop")
async def stop_mobile_agent(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    task_info = active_mobile_tasks.pop(user["user_id"], None)
    if task_info and task_info.get("process_task"):
        task_info["process_task"].cancel()
        return {"status": "stopped"}
    return {"status": "no_active_task"}


@router.post("/api/mobile-agent/run")
async def run_mobile_agent(request: MobileAgentRunRequest, req: Request):
    """SSE endpoint: streams mobile agent step updates to the client."""
    user = get_current_user(req)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")



    user_id = user["user_id"]

    task = request.task.strip()
    if not task:
        raise HTTPException(status_code=400, detail="Task cannot be empty.")

    run_config = request.config if request.config else global_config
    appium_config = request.appium_config or {}
    queue: asyncio.Queue = asyncio.Queue()
    history = []

    async def process_wrapper():
        await run_mobile_agent_stream(
            task=task,
            config=run_config,
            queue=queue,
            appium_config=appium_config,
        )

    process_task = asyncio.create_task(process_wrapper())
    task_info = {
        "task": task,
        "queue": queue,
        "process_task": process_task,
        "history": history,
    }
    active_mobile_tasks[user_id] = task_info

    async def event_generator():
        for hist_event in task_info["history"]:
            yield "data: " + json.dumps(hist_event) + "\n\n"

        q = task_info["queue"]
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=3600.0)
                    task_info["history"].append(event)
                    yield "data: " + json.dumps(event) + "\n\n"
                    if event.get("type") in ("done", "error"):
                        active_mobile_tasks.pop(user_id, None)
                        break
                except asyncio.TimeoutError:
                    yield "data: " + json.dumps({"type": "error", "text": "SSE Connection timeout."}) + "\n\n"
                    break
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
