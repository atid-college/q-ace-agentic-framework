import asyncio
import os
import json
from typing import Any, Dict, Optional
from core.base_tool import BaseTool
from handlers.mobile_handler import run_mobile_agent_stream

class MobileTool(BaseTool):
    """
    A tool to execute end-to-end mobile automation workflows using the Mobile Agent via Appium.
    """

    @property
    def name(self) -> str:
        return "mobile_tool"

    @property
    def description(self) -> str:
        return (
            "An agentic tool for mobile application automation and interaction.\n"
            "Arguments required:\n"
            "- 'task': A detailed natural language description of the mobile task to perform.\n"
            "This tool will connect to the configured Appium server and autonomously interact with the mobile app."
        )

    async def execute(self, **kwargs) -> Any:
        task = kwargs.get("task")
        
        if not task:
            return {"status": "error", "message": "'task' is strictly required."}
            
        global_config = kwargs.get("_global_config", {"base_url": "http://localhost:11434"})
        appium_config = kwargs.get("_appium_config", {"platformName": "Android", "serverUrl": "http://localhost:4723"})
        
        queue = asyncio.Queue()
        
        # Start the runner in the background
        process_task = asyncio.create_task(run_mobile_agent_stream(
            task=task,
            config=global_config,
            queue=queue,
            appium_config=appium_config
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
            final_result = "Mobile agent timed out after 1 hour."
            is_success = False
        finally:
            process_task.cancel()
            
        return {
            "status": "success" if is_success else "error",
            "message": final_result,
            "logs": logs
        }
