"""
Agent Chat (orchestrator) endpoints.
Routes: /api/chats/*, /api/chat (SSE stream)
"""

import asyncio
import json
import sqlite3

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from routers.dependencies import get_current_user, _get_user_config, registry, db_update_queue
from core.orchestrator import Orchestrator
from core.llm_client import LLMClient

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    prompt: str
    session_id: Optional[int] = None


class ChatSessionCreate(BaseModel):
    title: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/api/chats")
def list_chats(request: Request):
    """Lists all chat sessions for the current user."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conn = None
    try:
        conn = sqlite3.connect("data/q-ace.db", timeout=10.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        user_id = user.get("user_id")
        if not user_id:
            cursor.execute("SELECT id FROM users WHERE username = ?", (user.get("sub"),))
            db_user = cursor.fetchone()
            user_id = db_user["id"] if db_user else 1

        cursor.execute(
            "SELECT id, title, created_at FROM chat_sessions WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        sessions = [dict(row) for row in cursor.fetchall()]

        if not sessions:
            cursor.execute("INSERT INTO chat_sessions (user_id, title) VALUES (?, ?)", (user_id, "API to Database Agent Flow"))
            session1_id = cursor.lastrowid
            s1_messages = [
                ("user", "Fetch all users from the /users endpoint and verify if they exist in the local SQLite database."),
                ("assistant", "I will start by fetching the users via the API tool, then I will query the SQLite database to verify their existence."),
                ("assistant", '{"type": "workflow", "title": "Verification Flow", "status": "Completed", "steps": [{"id": 1, "label": "Fetch API Data", "tool": "api", "status": "completed"}, {"id": 2, "label": "Parse JSON", "tool": "ai", "status": "completed"}, {"id": 3, "label": "Query SQLite", "tool": "sqlite", "status": "completed"}, {"id": 4, "label": "AI Verification", "tool": "ai", "status": "completed"}]}'),
            ]
            for role, content in s1_messages:
                msg_type = "workflow" if content.startswith("{") else "text"
                cursor.execute("INSERT INTO chat_messages (session_id, role, content, type) VALUES (?, ?, ?, ?)", (session1_id, role, content, msg_type))

            cursor.execute("INSERT INTO chat_sessions (user_id, title) VALUES (?, ?)", (user_id, "Test Gen Agent to Jenkins Flow"))
            session2_id = cursor.lastrowid
            s2_messages = [
                ("user", "Analyze the login-spec.pdf and generate automation scripts for Jenkins."),
                ("assistant", "Analyzing the technical specification now. I will extract the requirements and map them to Jenkins pipeline steps."),
                ("assistant", '{"type": "workflow", "title": "Automation Pipeline", "status": "Completed", "steps": [{"id": 1, "label": "Analyze PDF Spec", "tool": "spec_analyzer", "status": "completed"}, {"id": 2, "label": "Generate Scripts", "tool": "ai", "status": "completed"}, {"id": 3, "label": "Jenkins Integration", "tool": "jenkins", "status": "completed"}]}'),
            ]
            for role, content in s2_messages:
                msg_type = "workflow" if content.startswith("{") else "text"
                cursor.execute("INSERT INTO chat_messages (session_id, role, content, type) VALUES (?, ?, ?, ?)", (session2_id, role, content, msg_type))

            cursor.execute("INSERT INTO chat_sessions (user_id, title) VALUES (?, ?)", (user_id, "E2E Regression & Reporting Flow"))
            session3_id = cursor.lastrowid
            s3_messages = [
                ("user", "Pull the latest code from GitHub, analyze the test specs, run Browser Agent E2E UI tests, update Qase test runs, and alert the team on Slack."),
                ("assistant", "Starting full E2E orchestration pipeline."),
                ("assistant", '{"type": "workflow", "title": "E2E Regression Suite", "status": "Completed", "steps": [{"id": 1, "label": "Pull Code", "tool": "github", "status": "completed"}, {"id": 2, "label": "Analyze Tests", "tool": "spec_analyzer", "status": "completed"}, {"id": 3, "label": "Run UI Tests", "tool": "browser_agent", "status": "completed"}, {"id": 4, "label": "Upload Results", "tool": "api", "status": "completed"}, {"id": 5, "label": "Alert Team", "tool": "slack", "status": "completed"}]}'),
            ]
            for role, content in s3_messages:
                msg_type = "workflow" if content.startswith("{") else "text"
                cursor.execute("INSERT INTO chat_messages (session_id, role, content, type) VALUES (?, ?, ?, ?)", (session3_id, role, content, msg_type))

            cursor.execute("INSERT INTO chat_sessions (user_id, title) VALUES (?, ?)", (user_id, "Intelligent API Validation Flow"))
            session4_id = cursor.lastrowid
            s4_messages = [
                ("user", "Fetch the latest user creation API, use AI to validate the schema, trigger the Jenkins backend sync job, verify SQLite state, and automatically open Jira bugs if data drops."),
                ("assistant", "Executing end-to-end API validation flow across microservices."),
                ("assistant", '{"type": "workflow", "title": "API Validation Chain", "status": "Completed", "steps": [{"id": 1, "label": "Fetch API data", "tool": "api", "status": "completed"}, {"id": 2, "label": "AI Schema Validation", "tool": "ai", "status": "completed"}, {"id": 3, "label": "Sync Backend", "tool": "jenkins", "status": "completed"}, {"id": 4, "label": "Validate Database", "tool": "sqlite", "status": "completed"}, {"id": 5, "label": "Create Jira Bug", "tool": "jira", "status": "completed"}]}'),
            ]
            for role, content in s4_messages:
                msg_type = "workflow" if content.startswith("{") else "text"
                cursor.execute("INSERT INTO chat_messages (session_id, role, content, type) VALUES (?, ?, ?, ?)", (session4_id, role, content, msg_type))

            conn.commit()
            cursor.execute(
                "SELECT id, title, created_at FROM chat_sessions WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            )
            sessions = [dict(row) for row in cursor.fetchall()]

        return sessions
    except Exception as e:
        import traceback
        with open("error.log", "w") as f:
            traceback.print_exc(file=f)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


@router.post("/api/chats")
async def create_chat(payload: ChatSessionCreate, request: Request):
    """Creates a new chat session."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conn = sqlite3.connect("data/q-ace.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chat_sessions (user_id, title) VALUES (?, ?)", (user["user_id"], payload.title))
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": session_id, "title": payload.title}


@router.get("/api/chats/{session_id}")
def get_chat_history(session_id: int, request: Request):
    """Retrieves all messages for a specific session."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conn = sqlite3.connect("data/q-ace.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT user_id FROM chat_sessions WHERE id = ?", (session_id,))
    session = cursor.fetchone()
    if not session or session["user_id"] != user["user_id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Forbidden")

    cursor.execute(
        "SELECT role, content, type, timestamp FROM chat_messages WHERE session_id = ? ORDER BY timestamp ASC",
        (session_id,),
    )
    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return messages


@router.delete("/api/chats/{session_id}")
async def delete_chat(session_id: int, request: Request):
    """Deletes a chat session."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conn = sqlite3.connect("data/q-ace.db")
    cursor = conn.cursor()

    cursor.execute("SELECT user_id FROM chat_sessions WHERE id = ?", (session_id,))
    session_row = cursor.fetchone()
    if not session_row or session_row[0] != user["user_id"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Forbidden")

    cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.post("/api/chat")
async def chat_endpoint(request: ChatRequest, req: Request):
    """Chat endpoint using SSE streaming."""
    user = get_current_user(req)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    session_id = request.session_id

    if not session_id:
        def _create_session():
            conn = sqlite3.connect("data/q-ace.db")
            cursor = conn.cursor()
            title = request.prompt[:30] + ("..." if len(request.prompt) > 30 else "")
            cursor.execute("INSERT INTO chat_sessions (user_id, title) VALUES (?, ?)", (user["user_id"], title))
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return new_id
        session_id = await asyncio.to_thread(_create_session)

    def _save_user_msg():
        conn = sqlite3.connect("data/q-ace.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_messages (session_id, role, content, type) VALUES (?, ?, ?, ?)",
            (session_id, "user", request.prompt, "text"),
        )
        conn.commit()
        conn.close()
    await asyncio.to_thread(_save_user_msg)

    cfg = _get_user_config(req)
    provider = LLMClient.get_provider(cfg)
    orchestrator = Orchestrator(provider=provider, registry=registry, global_config=cfg)
    queue = asyncio.Queue()
    msg_id_container = []

    async def stream_orchestrator():
        try:
            def _init_db():
                conn = sqlite3.connect("data/q-ace.db")
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO chat_messages (session_id, role, content, type) VALUES (?, ?, ?, ?)",
                    (session_id, "assistant", json.dumps({"type": "workflow", "status": "In Progress", "steps": []}), "workflow"),
                )
                mid = cursor.lastrowid
                conn.commit()
                conn.close()
                return mid

            mid = await asyncio.to_thread(_init_db)
            msg_id_container.append(mid)

            final_response = await orchestrator.chat(request.prompt, queue)

            def _update_final():
                conn = sqlite3.connect("data/q-ace.db")
                cursor = conn.cursor()
                cursor.execute("UPDATE chat_messages SET content = ? WHERE id = ?", (final_response, mid))
                conn.commit()
                conn.close()
            await asyncio.to_thread(_update_final)
        except Exception as e:
            await queue.put({"type": "error", "text": str(e)})

    asyncio.create_task(stream_orchestrator())

    async def event_generator():
        yield f"data: {json.dumps({'type': 'session_init', 'session_id': session_id})}\n\n"
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=600.0)

                    if event.get("type") == "workflow" and msg_id_container:
                        mid = msg_id_container[0]
                        await db_update_queue.put((mid, json.dumps(event)))

                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("type") == "done" or event.get("type") == "error":
                        break
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'error', 'text': 'Timeout'})}\n\n"
                    break
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'text': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
