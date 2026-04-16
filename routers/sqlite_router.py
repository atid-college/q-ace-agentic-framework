"""
SQLite Database Agent history and stats endpoints.
Routes: /api/sqlite/*
"""

import json
import sqlite3
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any

from routers.dependencies import get_current_user

router = APIRouter()


@router.get("/api/sqlite/history")
async def get_db_agent_history(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    conn = sqlite3.connect("data/q-ace.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM db_agent_history WHERE user_id = ? ORDER BY timestamp DESC",
        (user["user_id"],),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    for row in rows:
        try:
            row["result"] = json.loads(row["result_json"])
        except Exception:
            row["result"] = {}
        try:
            row["ai_analysis"] = json.loads(row["ai_analysis"]) if row.get("ai_analysis") else None
        except Exception:
            row["ai_analysis"] = None
    return rows


@router.post("/api/sqlite/history")
async def save_db_agent_history(data: Dict[str, Any], request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    conn = sqlite3.connect("data/q-ace.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO db_agent_history (user_id, prompt, result_json, active_db, sample_db, ai_analysis, is_verified)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user["user_id"],
            data.get("prompt"),
            json.dumps(data.get("result", {})),
            data.get("activeDb"),
            data.get("sampleDb"),
            json.dumps(data.get("aiAnalysis")) if data.get("aiAnalysis") else None,
            data.get("isVerified"),
        ),
    )
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.delete("/api/sqlite/history/{history_id}")
async def delete_db_agent_history_item(history_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    conn = sqlite3.connect("data/q-ace.db")
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM db_agent_history WHERE id=? AND user_id=?",
        (history_id, user["user_id"]),
    )
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.get("/api/sqlite/stats")
async def get_sqlite_stats(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    conn = sqlite3.connect("data/q-ace.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT is_verified, timestamp FROM db_agent_history WHERE user_id = ? ORDER BY timestamp DESC",
        (user["user_id"],),
    )
    rows = cursor.fetchall()
    conn.close()

    total = len(rows)
    failed = sum(1 for r in rows if r["is_verified"] is False)
    success = total - failed
    rate = round((success / total) * 100) if total > 0 else 0

    today = datetime.utcnow().date()
    daily_stats = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = sum(
            1 for r in rows
            if datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S").date() == day
        )
        daily_stats.append({"date": day.strftime("%Y-%m-%d"), "count": count})

    return {"total": total, "failed": failed, "success": success, "rate": rate, "daily": daily_stats}
