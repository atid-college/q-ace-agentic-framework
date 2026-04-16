"""
Browser Agent endpoints: history, stats, config, docs, SSE run, analyze.
Routes: /api/browser-agent/*
"""

import os
import asyncio
import json
import sqlite3
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Request, Response, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from routers.dependencies import get_current_user, _get_user_config, active_browser_tasks
from handlers.browser_handler import run_agent_stream
from core.auth_utils import verify_access_token
from core.suite_adapter import load_suite, UnsupportedFormatError, SuiteParseError

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class BrowserAgentRunRequest(BaseModel):
    task: str
    token: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    agent_config: Optional[Dict[str, Any]] = None
    llm_config: Optional[Dict[str, Any]] = None
    browser_config: Optional[Dict[str, Any]] = None
    reattach: bool = False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/api/browser-agent/docs/{filename}")
async def get_browser_doc(filename: str, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    doc_path = os.path.join("data", "browser-agent-docs", filename)
    if not os.path.exists(doc_path):
        raise HTTPException(status_code=404, detail="Documentation not found")

    with open(doc_path, "r", encoding="utf-8") as f:
        return Response(content=f.read(), media_type="text/markdown")


@router.get("/api/browser-agent/active-task")
async def get_active_browser_task(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    task_info = active_browser_tasks.get(user["user_id"])
    if task_info:
        return {"active": True, "task": task_info["task"]}
    return {"active": False}


@router.post("/api/browser-agent/stop")
async def stop_browser_agent(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    task_info = active_browser_tasks.pop(user["user_id"], None)
    if task_info and task_info.get("process_task"):
        task_info["process_task"].cancel()
        return {"status": "stopped"}
    return {"status": "no_active_task"}


@router.get("/api/browser-agent/history")
async def get_browser_history(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    conn = sqlite3.connect("data/q-ace.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM browser_agent_history WHERE user_id = ? ORDER BY timestamp DESC",
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


@router.post("/api/browser-agent/history")
async def save_browser_history(data: Dict[str, Any], request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    conn = sqlite3.connect("data/q-ace.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO browser_agent_history (user_id, prompt, logs, history_json, result, status)
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


@router.delete("/api/browser-agent/history/clear")
async def clear_browser_history(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    conn = sqlite3.connect("data/q-ace.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM browser_agent_history WHERE user_id=?", (user["user_id"],))
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.delete("/api/browser-agent/history/{history_id}")
async def delete_browser_history(history_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    conn = sqlite3.connect("data/q-ace.db")
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM browser_agent_history WHERE id=? AND user_id=?",
        (history_id, user["user_id"]),
    )
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.post("/api/browser-agent/history/{history_id}/analyze")
async def analyze_browser_history(history_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    conn = sqlite3.connect("data/q-ace.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM browser_agent_history WHERE id=? AND user_id=?",
        (history_id, user["user_id"]),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="History not found")

    prompt = row["prompt"]
    result = row["result"] or "No final result."
    try:
        hist_json = json.loads(row["history_json"]) if row.get("history_json") else {}
    except Exception:
        hist_json = {}

    cursor.execute("SELECT provider FROM user_settings WHERE user_id=?", (user["user_id"],))
    settings_row = cursor.fetchone()
    provider = settings_row["provider"] if settings_row else "gemini"

    steps_context = []
    actions = hist_json.get("action_names", [])
    errors = hist_json.get("errors", [])
    thoughts = hist_json.get("model_thoughts", [])
    extracted = hist_json.get("extracted_content", [])
    urls = hist_json.get("urls", [])

    for i in range(len(actions)):
        step_data = f"Step {i+1}: Action=[{actions[i]}] URL=[{urls[i] if len(urls) > i else ''}]"
        if len(thoughts) > i and thoughts[i]:
            step_data += f"\n  Thought: {thoughts[i]}"
        if len(extracted) > i and extracted[i]:
            step_data += f"\n  Extracted: {extracted[i]}"
        if len(errors) > i and errors[i]:
            step_data += f"\n  ERROR: {errors[i]}"
        steps_context.append(step_data)

    context_str = "\n".join(steps_context)

    analysis_prompt = f"""
Analyze the following browser automation execution and provide insights.
User Request: {prompt}
Final Outcome: {result}

Execution Steps:
{context_str}

Please provide a concise but highly professional markdown report. Focus on:
1. Root Cause Analysis (if errors occurred or it failed).
2. Key Insights identifying why the agent took the paths it did.
3. Summary of data gathered vs data requested.
Do not wrap your entire response in a code block, format it directly as markdown.
"""

    from core.llm_client import get_llm_response
    try:
        cursor.execute("SELECT * FROM user_settings WHERE user_id=?", (user["user_id"],))
        full_settings = cursor.fetchone()

        provider_model = None
        if provider == "gemini":
            provider_model = full_settings["gemini_model"]
        elif provider == "ollama":
            provider_model = full_settings["ollama_model"]

        analysis_markdown = get_llm_response(
            prompt=analysis_prompt,
            provider=provider,
            model=provider_model,
            api_key=full_settings.get("api_key") if full_settings else None,
            base_url=full_settings.get("base_url") if full_settings else None,
        )

        cursor.execute(
            "UPDATE browser_agent_history SET ai_analysis=? WHERE id=?",
            (analysis_markdown, history_id),
        )
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

    conn.close()
    return {"status": "success", "analysis": analysis_markdown}


@router.get("/api/browser-agent/stats")
async def get_browser_agent_stats(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    conn = sqlite3.connect("data/q-ace.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) as total FROM browser_agent_history WHERE user_id = ?",
        (user["user_id"],),
    )
    total = cursor.fetchone()["total"]

    if total == 0:
        conn.close()
        return {"total": 0, "success": 0, "failed": 0, "rate": 0, "daily": []}

    cursor.execute(
        "SELECT history_json FROM browser_agent_history WHERE user_id = ?",
        (user["user_id"],),
    )
    rows = cursor.fetchall()

    success = 0
    failed = 0
    for r in rows:
        try:
            h = json.loads(r["history_json"])
            if h.get("is_successful"):
                success += 1
            else:
                failed += 1
        except Exception:
            failed += 1

    cursor.execute(
        """
        SELECT date(timestamp) as day, COUNT(*) as count
        FROM browser_agent_history
        WHERE user_id = ? AND timestamp >= date('now', '-7 days')
        GROUP BY day ORDER BY day ASC
        """,
        (user["user_id"],),
    )
    daily = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return {
        "total": total,
        "success": success,
        "failed": failed,
        "rate": round((success / total) * 100, 1) if total > 0 else 0,
        "daily": daily,
    }


@router.post("/api/browser-agent/analyze-all")
async def analyze_all_history(data: Dict[str, Any], request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    conn = sqlite3.connect("data/q-ace.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT prompt, result, timestamp FROM browser_agent_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 20",
        (user["user_id"],),
    )
    rows = cursor.fetchall()

    if not rows:
        conn.close()
        return {"analysis": "No execution history found to analyze."}

    history_summary = [
        f"- [{r['timestamp']}] Task: {r['prompt']} | Result: {r['result'][:100]}..."
        for r in rows
    ]
    summary_text = "\n".join(history_summary)

    analysis_prompt = f"""
I am an AI assistant analyzing a suite of browser automation runs. 
Here is the recent history of tasks and outcomes:
{summary_text}

Please provide a high-level "Dashboard Executive Summary":
1. Overall Performance: Are most tasks succeeding?
2. Common Themes: What kind of testing is the user focusing on?
3. Strategic Recommendations: Based on the failures or patterns, what should be improved in the automation suite?

Format as professional markdown.
"""

    from core.llm_client import get_llm_response
    try:
        cursor.execute("SELECT * FROM user_settings WHERE user_id=?", (user["user_id"],))
        full_settings = cursor.fetchone()

        provider = data.get("provider", "gemini")
        provider_model = None
        if provider == "gemini":
            provider_model = full_settings["gemini_model"]
        elif provider == "ollama":
            provider_model = full_settings["ollama_model"]

        analysis_markdown = get_llm_response(
            prompt=analysis_prompt,
            provider=provider,
            model=provider_model,
            api_key=full_settings.get("api_key") if full_settings else None,
            base_url=full_settings.get("base_url") if full_settings else None,
        )
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

    conn.close()
    return {"analysis": analysis_markdown}


@router.get("/api/browser-agent/config")
async def get_browser_agent_config(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    def _do_get():
        conn = sqlite3.connect("data/q-ace.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT agent_config, browser_config, llm_config FROM browser_agent_config WHERE user_id = ?",
            (user["user_id"],),
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    row = await asyncio.to_thread(_do_get)

    if row:
        return {
            "agent_config": json.loads(row["agent_config"]) if row["agent_config"] else {},
            "browser_config": json.loads(row["browser_config"]) if row["browser_config"] else {},
            "llm_config": json.loads(row["llm_config"]) if row["llm_config"] else {},
        }
    return {}


@router.post("/api/browser-agent/config")
async def save_browser_agent_config(data: Dict[str, Any], request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    agent_cfg = data.get("agent_config") or data.get("agentConfig", {})
    browser_cfg = data.get("browser_config") or data.get("browserConfig", {})
    llm_cfg = data.get("llm_config") or data.get("llmConfig", {})

    def _do_save():
        conn = sqlite3.connect("data/q-ace.db")
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO browser_agent_config (user_id, agent_config, browser_config, llm_config)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                agent_config=excluded.agent_config,
                browser_config=excluded.browser_config,
                llm_config=excluded.llm_config
            """,
            (user["user_id"], json.dumps(agent_cfg), json.dumps(browser_cfg), json.dumps(llm_cfg)),
        )
        conn.commit()
        conn.close()

    await asyncio.to_thread(_do_save)
    return {"status": "success"}


@router.get("/api/browser-agent/docs")
async def get_browser_agent_docs(request: Request):
    """Returns all markdown documentation for the browser agent."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)

    docs_dir = "data/browser-agent-docs"
    if not os.path.exists(docs_dir):
        return {"docs": []}

    docs = []
    for filename in sorted(os.listdir(docs_dir)):
        if filename.endswith(".md") and filename.lower() != "readme.md":
            path = os.path.join(docs_dir, filename)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            display_name = filename.replace(".md", "").replace("browser-use-", "").replace("-", " ").replace("_", " ")
            title = display_name.title()

            if "agent-params" in filename:
                title = "Agent Parameters"
            if "browser-params" in filename:
                title = "Browser Parameters"
            if "llms-params" in filename:
                title = "LLM Providers"
            if "output-format-history" in filename:
                title = "Output Format"
            if "tools-params" in filename:
                title = "Available Tools"
            if "supported-models" in filename:
                title = "Supported Models"

            docs.append({"filename": filename, "title": title, "content": content})

    return {"docs": docs}


@router.post("/api/browser-agent/upload-suite")
async def upload_browser_suite(request: Request, file: UploadFile = File(...)):
    """Parses an uploaded test suite file (JSON/CSV/YAML/MD) into a list of prompts."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    file_bytes = await file.read()
    filename = file.filename or "suite"

    try:
        prompts = load_suite(file_bytes, filename)
    except UnsupportedFormatError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SuiteParseError as e:
        raise HTTPException(status_code=422, detail=str(e))

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
    return {
        "prompts": prompts,
        "count": len(prompts),
        "format": ext,
        "filename": filename,
    }


@router.post("/api/browser-agent/run")
async def run_browser_agent(request: BrowserAgentRunRequest, req: Request):
    """SSE endpoint: streams browser-use agent step updates to the client."""
    user = get_current_user(req)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")



    user_id = user["user_id"]

    if request.reattach and user_id in active_browser_tasks:
        task_info = active_browser_tasks[user_id]
    else:
        task = request.task.strip()
        if not task:
            raise HTTPException(status_code=400, detail="Task cannot be empty.")

        run_config = request.config if request.config else _get_user_config(req)
        queue: asyncio.Queue = asyncio.Queue()
        history = []

        async def process_wrapper():
            await run_agent_stream(
                task=task,
                global_config=run_config,
                queue=queue,
                agent_config=request.agent_config,
                llm_config=request.llm_config,
                browser_config=request.browser_config,
            )

        process_task = asyncio.create_task(process_wrapper())
        task_info = {
            "task": task,
            "queue": queue,
            "process_task": process_task,
            "history": history,
        }
        active_browser_tasks[user_id] = task_info

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
                        active_browser_tasks.pop(user_id, None)
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
