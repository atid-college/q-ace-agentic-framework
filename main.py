import os
import asyncio
import sys
import json
import sqlite3

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import shared state (initializes global_config, handlers, registry, etc.)
from routers.dependencies import db_update_queue  # noqa: E402

# Import routers
from routers.config_router import router as config_router
from routers.auth_router import router as auth_router
from routers.chat_router import router as chat_router
from routers.sqlite_router import router as sqlite_router
from routers.api_agent_router import router as api_agent_router
from routers.browser_agent_router import router as browser_agent_router
from routers.mobile_agent_router import router as mobile_agent_router


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Q-ACE Agentic QA Framework")


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    # Start the DB update worker for persistent streaming
    asyncio.create_task(db_worker())

    # Ensure data dir exists
    os.makedirs("data", exist_ok=True)


async def db_worker():
    """Sequentially processes database updates to avoid SQLite lock contention."""
    while True:
        try:
            update_task = await db_update_queue.get()
            mid, content = update_task

            def _do_update():
                conn = sqlite3.connect("data/q-ace.db", timeout=30)
                cursor = conn.cursor()
                cursor.execute("UPDATE chat_messages SET content = ? WHERE id = ?", (content, mid))
                conn.commit()
                conn.close()

            await asyncio.to_thread(_do_update)
            db_update_queue.task_done()
        except Exception as e:
            print(f"CRITICAL DB WORKER ERROR: {e}")
            await asyncio.sleep(1)


# ---------------------------------------------------------------------------
# Misc endpoints
# ---------------------------------------------------------------------------

@app.get("/api/debug/heartbeat")
async def debug_heartbeat():
    print("\n[DEBUG] HEARTBEAT RECEIVED!", flush=True)
    return {"status": "alive"}


@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def well_known_devtools():
    """Satisfies Chrome DevTools discovery requests to clear logs."""
    return {}


# ---------------------------------------------------------------------------
# Include routers
# ---------------------------------------------------------------------------

app.include_router(config_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(sqlite_router)
app.include_router(api_agent_router)
app.include_router(browser_agent_router)
app.include_router(mobile_agent_router)


# ---------------------------------------------------------------------------
# Static files (must be mounted last)
# ---------------------------------------------------------------------------

app.mount("/", StaticFiles(directory="static", html=True), name="static")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", 8090))
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
