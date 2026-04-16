import asyncio
import os
import sys
import json
import subprocess
import traceback
import threading
from typing import Dict, Any, Optional
from handlers.base_handler import BaseHandler

class BrowserHandler(BaseHandler):
    """
    Handler for the Browser Agent tool powered by the browser-use library.
    """
    @property
    def tool_id(self) -> str: return "browser_agent"
    @property
    def tool_name(self) -> str: return "Browser Agent"
    @property
    def icon(self) -> str: return "globe"

    def get_ui_definition(self) -> Dict[str, Any]:
        return {
            "title": "Browser Agent",
            "description": "AI-powered browser automation. Watch it work in real-time.",
            "is_placeholder": False,
        }

    async def handle_action(self, action: str, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "error", "message": "Use the /api/browser-agent/run SSE endpoint instead."}

async def run_agent_stream(task: str, global_config: Dict[str, Any], queue: asyncio.Queue, agent_config: Optional[Dict[str, Any]] = None, llm_config: Optional[Dict[str, Any]] = None, browser_config: Optional[Dict[str, Any]] = None):
    """
    Runs a browser-use Agent in a separate subprocess using the .venv environment.
    Uses subprocess.Popen and threads for robust Windows compatibility.
    """
    loop = asyncio.get_event_loop()
    try:
        # Determine the python executable in .venv
        cwd = os.getcwd()
        python_exe = os.path.join(cwd, ".venv", "Scripts", "python.exe")
        if not os.path.exists(python_exe):
            # Fallback for linux or if naming is different
            python_exe = os.path.join(cwd, ".venv", "bin", "python")
        
        if not os.path.exists(python_exe):
            await queue.put({"type": "error", "text": f"Could not find Python in .venv. Target path: {python_exe}"})
            return

        runner_script = os.path.join(cwd, "handlers", "browser_agent_runner.py")
        config_json = json.dumps(global_config)
        agent_config_json = json.dumps(agent_config or {})
        llm_config_json = json.dumps(llm_config or {})
        browser_config_json = json.dumps(browser_config or {})

        await queue.put({"type": "step", "text": "🚀 Launching agent subprocess (Robust Popen)..."})

        # Create the subprocess using synchronous Popen
        # We use CREATE_NEW_PROCESS_GROUP on Windows to allow signal handling and isolation
        process = subprocess.Popen(
            [python_exe, runner_script, task, config_json, agent_config_json, llm_config_json, browser_config_json],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            text=True,
            bufsize=1,
            creationflags=getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0) if os.name == 'nt' else 0
        )

        def listen_to_stream(stream, is_stderr=False):
            try:
                for line in iter(stream.readline, ''):
                    line_text = line.strip()
                    if not line_text:
                        continue

                    if is_stderr:
                        # Filter out known harmless warnings
                        if "MP4 recording requires optional dependencies" in line_text:
                            continue
                            
                        # Always forward stderr as a visible error/progress event
                        loop.call_soon_threadsafe(queue.put_nowait, {
                            "type": "step",
                            "text": f"[Subprocess STDERR] {line_text}"
                        })
                    else:
                        try:
                            # Attempt to parse as JSON from our runner
                            update = json.loads(line_text)
                            loop.call_soon_threadsafe(queue.put_nowait, update)
                        except json.JSONDecodeError:
                            # Forward non-JSON stdout lines as generic step info
                            loop.call_soon_threadsafe(queue.put_nowait, {
                                "type": "step",
                                "text": f"[Subprocess] {line_text}"
                            })
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "text": f"Stream Reader Error: {str(e)}"})

        # Start threads to read stdout and stderr
        t_out = threading.Thread(target=listen_to_stream, args=(process.stdout,), daemon=True)
        t_err = threading.Thread(target=listen_to_stream, args=(process.stderr, True), daemon=True)
        
        t_out.start()
        t_err.start()

        # Wait for the process to finish in a non-blocking way
        while process.poll() is None:
            await asyncio.sleep(0.5)

        # Wait for threads to finish flushing
        t_out.join(timeout=5)
        t_err.join(timeout=5)

        # Emit error if process returned non-zero
        if process.returncode != 0:
            loop.call_soon_threadsafe(queue.put_nowait, {
                "type": "error",
                "text": f"Browser agent subprocess exited with code {process.returncode}. Check the [Subprocess STDERR] messages above for details."
            })

    except asyncio.CancelledError:
        if process:
            # Windows robust termination
            try:
                if os.name == 'nt':
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
                else:
                    process.terminate()
            except: pass
        raise
    except Exception as e:
        await queue.put({"type": "error", "text": f"Handler Error: {str(e)}\n{traceback.format_exc()}"})
    finally:
        if process and process.poll() is None:
            try: process.terminate()
            except: pass
