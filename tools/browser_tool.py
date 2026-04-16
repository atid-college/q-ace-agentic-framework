import asyncio
import os
import json
from typing import Any, Dict, Optional
from core.base_tool import BaseTool
from handlers.browser_handler import run_agent_stream

class BrowserTool(BaseTool):
    """
    A tool to execute end-to-end browser automation workflows using the Browser Agent.
    """

    @property
    def name(self) -> str:
        return "browser_tool"

    @property
    def description(self) -> str:
        return (
            "An agentic tool to execute end-to-end UI automation and browser tasks.\n"
            "Arguments required:\n"
            "- 'task': A detailed natural language description of the browser task to perform.\n"
            "This tool will spawn a headless or visible browser, navigate, interact with elements, and return the final result."
        )

    async def execute(self, **kwargs) -> Any:
        task = kwargs.get("task")
        
        if not task:
            return {"status": "error", "message": "'task' is strictly required."}
            
        # We need the global config roughly. We get it from context if passed, else fallback object.
        global_config = kwargs.get("_global_config", {"base_url": "http://localhost:11434"})
        
        queue = asyncio.Queue()
        
        # Start the runner in the background
        process_task = asyncio.create_task(run_agent_stream(
            task=task,
            global_config=global_config,
            queue=queue
        ))
        
        final_result = None
        logs = []
        is_success = False
        
        orchestrator_queue = kwargs.get("_queue")
        step_id = kwargs.get("_step_id")

        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=3600.0)
                event_type = event.get("type")
                
                if event_type == "step":
                    step_text = event.get("text", "")
                    logs.append(step_text)
                    if orchestrator_queue and step_id:
                        await orchestrator_queue.put({
                            "type": "tool_progress",
                            "step_id": step_id,
                            "text": step_text
                        })
                elif event_type == "done":
                    final_result = event.get("text", "Task completed.")
                    is_success = True
                    break
                elif event_type == "error":
                    final_result = event.get("text", "An error occurred.")
                    is_success = False
                    break
                    
        except asyncio.TimeoutError:
            final_result = "Browser agent timed out after 1 hour."
            is_success = False
        finally:
            process_task.cancel()
            
        return {
            "status": "success" if is_success else "error",
            "message": final_result,
            "logs": logs
        }
