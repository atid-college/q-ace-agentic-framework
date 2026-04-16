import json
import asyncio
from typing import Any, Dict, List, Optional
from core.context_manager import ContextManager
from core.tool_registry import ToolRegistry
from providers.base_provider import BaseLLMProvider

class Orchestrator:
    """
    Main engine that orchestrates the flow between the user, LLM, and tools.
    """
    def __init__(self, provider: BaseLLMProvider, registry: ToolRegistry, global_config: Dict[str, Any] = None):
        self.provider = provider
        self.registry = registry
        self.global_config = global_config or {}
        self.context = ContextManager()

    def _build_system_prompt(self, tools_metadata: List[Dict[str, Any]]) -> str:
        tools_desc = "\n\n".join([f"- **{t['name']}**: {t['description']}" for t in tools_metadata])
        sys_prompt = f"""
You are the Q-ACE Master Orchestrator, an intelligent agent that coordinates multiple tools to accomplish complex multi-step workflows.

AVAILABLE TOOLS:
{tools_desc}

INSTRUCTIONS:
1. Break the user's request into a series of steps. Use ONE tool at a time.
2. The user's request may contain multiple clauses joined by words like "then", "and", "also", "next", "after that" - each clause requires its own separate tool call.
3. After each tool call you will receive results. Use these to inform the NEXT tool call.
4. You MUST call ALL relevant tools before declaring "done". Do NOT stop early.
5. Only output "done" when ALL parts of the user's request have been executed by actual tool calls.

To use a tool, output ONLY valid JSON:
{{
  "action": "call_tool",
  "tool_name": "<name of the tool>",
  "arguments": {{
    "<arg1>": "<value1>"
  }},
  "reasoning": "<why you are calling this tool>"
}}

When ALL parts of the user's request are complete (all tools called, all results received), output ONLY:
{{
  "action": "done",
  "reasoning": "<summary of what was accomplished>"
}}

CRITICAL: Output exactly ONE JSON object per response. No extra text, no markdown outside JSON.
"""
        return sys_prompt.strip()

    async def chat(self, prompt: str, queue: asyncio.Queue = None) -> str:
        """
        Processes a user prompt, orchestrates tools autonomously, and returns the agent's workflow JSON response.
        If a queue is provided, it streams live updates.
        """
        tools_metadata = self.registry.get_tools_metadata()
        system_prompt = self._build_system_prompt(tools_metadata)
        
        # We start a fresh context for this orchestration loop to stay focused
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        workflow_steps = []
        max_turns = 8
        step_id = 1
        
        async def emit_update(status="In Progress"):
            if queue:
                await queue.put({
                    "type": "workflow",
                    "title": f"Autonomous Execution ({len(workflow_steps)} steps)",
                    "status": status,
                    "steps": workflow_steps
                })
        
        for turn in range(max_turns):
            # Tell UI we are thinking
            if queue:
                # Add a temporary thinking step
                temp_steps = list(workflow_steps)
                temp_steps.append({
                    "id": step_id, "label": "LLM Reasoning...", "tool": "ai", 
                    "status": "running", "result": ""
                })
                await queue.put({
                    "type": "workflow",
                    "title": f"Autonomous Execution ({len(temp_steps)} steps)",
                    "status": "In Progress",
                    "steps": temp_steps
                })

            # 1. Ask the LLM what to do
            try:
                llm_response = await self.provider.generate_response(messages=messages)
                response_text = llm_response["content"].strip()
                print(f"[ORCHESTRATOR] Turn {turn+1} - LLM raw response: {response_text[:300]}", flush=True)
            except Exception as e:
                print(f"[ORCHESTRATOR] LLM communication error: {e}", flush=True)
                workflow_steps.append({
                    "id": step_id, "label": "LLM Orchestration Failed", "tool": "ai", 
                    "status": "error", "result": f"Error communicating with LLM: {str(e)}"
                })
                break
                
            # Clean up markdown if LLM wrapped it
            if response_text.startswith("```json"): response_text = response_text[7:]
            if response_text.startswith("```"): response_text = response_text[3:]
            if response_text.endswith("```"): response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Parse the LLM action
            try:
                action_data = json.loads(response_text)
            except json.JSONDecodeError:
                # Capture the reasoning / failure for the user
                workflow_steps.append({
                    "id": step_id, 
                    "label": "LLM Reasoning Error", 
                    "tool": "ai", 
                    "status": "error", 
                    "result": f"LLM failed to provide a valid JSON action. \n\nRaw Response:\n{response_text}"
                })
                await emit_update("In Progress")
                step_id += 1
                
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": "ERROR: You returned invalid JSON or conversational text. Return ONLY valid JSON matching the requested schema."})
                continue
                
            action = action_data.get("action")
            reasoning = action_data.get("reasoning", "Executing next step...")
            print(f"[ORCHESTRATOR] Parsed action: {action}, tool: {action_data.get('tool_name', 'N/A')}", flush=True)
            
            if action == "done":
                # Workflow is complete
                workflow_steps.append({
                    "id": step_id,
                    "label": "Workflow Complete",
                    "tool": "ai",
                    "status": "completed",
                    "result": reasoning
                })
                await emit_update("Completed")
                break
                
            elif action == "call_tool":
                tool_name = action_data.get("tool_name")
                arguments = action_data.get("arguments", {})
                
                tool = self.registry.get_tool(tool_name)
                
                if not tool:
                    messages.append({"role": "assistant", "content": json.dumps(action_data)})
                    messages.append({"role": "user", "content": f"ERROR: Tool '{tool_name}' not found. Please select from available tools."})
                    continue
                
                messages.append({"role": "assistant", "content": json.dumps(action_data)})
                
                # Update UI that tool is running
                if queue:
                    temp_steps = list(workflow_steps)
                    temp_steps.append({
                        "id": step_id, "label": f"Running {tool_name}...", "tool": tool_name.replace('_tool', ''), 
                        "status": "running", "result": "Executing tool..."
                    })
                    await queue.put({
                        "type": "workflow",
                        "title": f"Autonomous Execution ({len(temp_steps)} steps)",
                        "status": "In Progress",
                        "steps": temp_steps
                    })
                
                
                # Inject context variables
                arguments["_provider"] = self.provider
                arguments["_queue"] = queue
                arguments["_step_id"] = step_id
                # Pass the real global config so tools (like browser) have API keys
                arguments["_global_config"] = self.global_config
                arguments["_appium_config"] = {"platformName": "Android", "serverUrl": "http://localhost:4723"}

                # Execute the tool
                try:
                    result = await tool.execute(**arguments)
                    
                    # Store step for UI
                    workflow_steps.append({
                        "id": step_id,
                        "label": f"Run {tool_name}",
                        "tool": tool_name.replace('_tool', ''),
                        "status": "completed" if result.get("status") != "error" else "error",
                        "result": json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
                    })
                    
                    # Feed result back to LLM
                    messages.append({
                        "role": "user", 
                        "content": f"TOOL RESULT for {tool_name}:\n{json.dumps(result)}"
                    })
                    
                    await emit_update("In Progress")
                    
                except Exception as e:
                    workflow_steps.append({
                        "id": step_id,
                        "label": f"Error running {tool_name}",
                        "tool": tool_name.replace('_tool', ''),
                        "status": "error",
                        "result": str(e)
                    })
                    messages.append({
                        "role": "user", 
                        "content": f"TOOL ERROR for {tool_name}:\n{str(e)}"
                    })
                    
                    await emit_update("In Progress")
                    
                step_id += 1
                
            else:
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": "ERROR: Unknown action. Must be 'call_tool' or 'done'."})

        # Ensure we don't return an empty workflow
        if not workflow_steps:
             workflow_steps.append({
                 "id": 1, "label": "Execution Error", "tool": "ai", "status": "error",
                 "result": "Orchestrator failed to parse any valid steps from the LLM."
             })
             await emit_update("Error")

        if queue:
            await queue.put({"type": "done"})

        # Return the structured JSON for the frontend chat view
        final_workflow = {
            "type": "workflow",
            "title": f"Autonomous Execution ({len(workflow_steps)} steps)",
            "status": "Completed" if action == 'done' else "Interrupted",
            "steps": workflow_steps
        }

        # Saving to generic context just in case
        self.context.add_message("user", prompt)
        self.context.add_message("assistant", json.dumps(final_workflow))

        return json.dumps(final_workflow)
