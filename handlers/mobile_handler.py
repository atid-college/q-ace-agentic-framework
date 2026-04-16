# Final reload trigger for strictly venv targeted packages
import asyncio
import json
import traceback
import xml.etree.ElementTree as ET
import re
from typing import Dict, Any, Optional

from handlers.base_handler import BaseHandler

try:
    from appium import webdriver
    APPIUM_AVAILABLE = True
except ImportError:
    APPIUM_AVAILABLE = False


class MobileHandler(BaseHandler):
    """
    Handler for the Mobile Agent tool powered by Appium.
    """
    @property
    def tool_id(self) -> str: return "mobile_agent"
    @property
    def tool_name(self) -> str: return "Mobile Agent"
    @property
    def icon(self) -> str: return "smartphone"

    def get_ui_definition(self) -> Dict[str, Any]:
        return {
            "title": "Mobile Agent",
            "description": "AI-powered mobile app automation via Appium.",
            "is_placeholder": False,
        }

    async def handle_action(self, action: str, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "error", "message": "Use the /api/mobile-agent/run SSE endpoint instead."}


def get_cleaned_ui_hierarchy(driver) -> str:
    """
    Fetches the page_source from Appium, parses the XML, and filters out non-interactive elements.
    """
    try:
        page_source = driver.page_source
        
        # Sanitize common Appium invalid XML characters/entities that crash strict parsers
        page_source = re.sub(r'&#[xX]?[0-9a-fA-F]+;', '', page_source)
        page_source = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', page_source)
        
        root = ET.fromstring(page_source.encode('utf-8'))
        cleaned_elements = []
        
        def traverse(node):
            clickable = node.attrib.get('clickable', 'false').lower() == 'true'
            focusable = node.attrib.get('focusable', 'false').lower() == 'true'
            text = node.attrib.get('text', '').strip()
            content_desc = node.attrib.get('content-desc', '').strip()
            resource_id = node.attrib.get('resource-id', '')
            
            if (clickable or focusable or text or content_desc) and resource_id:
                cleaned_elements.append({
                    "tag": node.tag.split('.')[-1],
                    "id": resource_id,
                    "text": text or content_desc
                })
            
            for child in node:
                traverse(child)
                
        traverse(root)
        # Simplify the representation to save LLM tokens
        return json.dumps(cleaned_elements)
    except Exception as e:
        return f"Error retrieving UI hierarchy: {str(e)}"


async def run_mobile_agent_stream(task: str, config: Dict[str, Any], queue: asyncio.Queue, appium_config: Dict[str, Any]):
    """
    Execution loop where the LLM analyzes the pruned XML and returns actions, streamed back via SSE.
    """
    driver = None
    try:
        if not APPIUM_AVAILABLE:
            await queue.put({'type': 'error', 'text': 'Appium-Python-Client is not installed. Please install it to use the Mobile Agent.'})
            return

        from core.llm_client import LLMClient
        await queue.put({'type': 'step', 'text': 'Starting Mobile Agent execution...'})
        
        caps = {
            "platformName": appium_config.get("platformName", "Android"),
            "automationName": "UiAutomator2"
        }
        if appium_config.get("udid"):
            caps["udid"] = appium_config.get("udid")
        if appium_config.get("appPackage"):
            caps["appPackage"] = appium_config.get("appPackage")
        if appium_config.get("appActivity"):
            caps["appActivity"] = appium_config.get("appActivity")
            
        server_url = appium_config.get("serverUrl", "http://localhost:4723")
        
        await queue.put({'type': 'step', 'text': f'Connecting to Appium server at {server_url}...'})
        # Appium Python Client 1.3 doesn't use options, so we use desired_capabilities instead
        driver = await asyncio.to_thread(webdriver.Remote, command_executor=server_url, desired_capabilities=caps)
        
        await queue.put({'type': 'step', 'text': 'Successfully connected to the device.'})
        
        provider_type = config.get("provider", "gemini")
        model = config.get("gemini", {}).get("model") if provider_type == "gemini" else config.get("ollama", {}).get("model")
        api_key = config.get("gemini", {}).get("api_key")
        base_url = config.get("ollama", {}).get("base_url")
        
        llm_settings = {
            "provider": provider_type,
            "api_key": api_key,
            "base_url": base_url
        }
        if model:
            llm_settings["model"] = model
            
        provider_instance = LLMClient.get_provider(llm_settings)
        
        # Give the app a moment to load
        await asyncio.sleep(2)
        
        # Max steps
        max_steps = 10
        
        for step in range(max_steps):
            await queue.put({'type': 'step', 'text': f'Step {step+1}: Analyzing UI state...'})
            
            # 1. Prune UI XML
            ui_state = await asyncio.to_thread(get_cleaned_ui_hierarchy, driver)
            
            if ui_state.startswith("Error retrieving UI hierarchy:"):
                await queue.put({'type': 'error', 'text': f"Appium XML Error: {ui_state}"})
                break
                
            # 2. Ask LLM
            prompt = f"""
You are an autonomous mobile agent.
Your objective: {task}

Current Cleaned UI State:
{ui_state}

What should the next action be? 
Return ONLY valid JSON in this format:
{{
  "action": "click|type|swipe|done",
  "id": "resource-id (if click or type)",
  "text": "text to type (if type)",
  "direction": "up|down|left|right (if swipe)",
  "reasoning": "Brief explanation of why you chose this action"
}}
"""
            
            messages = [{"role": "user", "content": prompt}]
            try:
                response = await provider_instance.generate_response(messages)
                llm_reply = response["content"]
            except Exception as ex:
                await queue.put({'type': 'error', 'text': f'Failed to get LLM response: {str(ex)}'})
                break
            
            # Parse JSON safely
            try:
                response_text = llm_reply.strip()
                if response_text.startswith("```json"): response_text = response_text[7:]
                if response_text.startswith("```"): response_text = response_text[3:]
                if response_text.endswith("```"): response_text = response_text[:-3]
                action_data = json.loads(response_text.strip())
            except Exception as e:
                await queue.put({'type': 'error', 'text': f'Failed to parse LLM response: {llm_reply}'})
                break
                
            reasoning = action_data.get('reasoning', 'No reasoning provided')
            await queue.put({'type': 'step', 'text': f"🤔 Reasoning: {reasoning}"})
            
            action = action_data.get("action")
            res_id = action_data.get("id")
            
            if action == "done":
                await queue.put({'type': 'done', 'text': 'Agent marked the task as successfully completed.', 'result': 'Task completed.'})
                break
            elif action == "click":
                if not res_id:
                    await queue.put({'type': 'error', 'text': "Click action requires an 'id'."})
                    continue
                await queue.put({'type': 'step', 'text': f"🖱️ Clicking element: {res_id}"})
                try:
                    el = await asyncio.to_thread(driver.find_element, "id", res_id)
                    await asyncio.to_thread(el.click)
                except Exception as ex:
                    await queue.put({'type': 'error', 'text': f"Action failed: {str(ex)}"})
            elif action == "type":
                if not res_id:
                    await queue.put({'type': 'error', 'text': "Type action requires an 'id'."})
                    continue
                text = action_data.get("text", "")
                await queue.put({'type': 'step', 'text': f"⌨️ Typing '{text}' into: {res_id}"})
                try:
                    el = await asyncio.to_thread(driver.find_element, "id", res_id)
                    await asyncio.to_thread(el.send_keys, text)
                except Exception as ex:
                    await queue.put({'type': 'error', 'text': f"Action failed: {str(ex)}"})
            elif action == "swipe":
                direction = action_data.get("direction")
                await queue.put({'type': 'step', 'text': f"👆 Swiping {direction}..."})
                try:
                    sz = await asyncio.to_thread(driver.get_window_size)
                    w, h = sz['width'], sz['height']
                    if direction == "up":
                        await asyncio.to_thread(driver.swipe, w//2, int(h*0.8), w//2, int(h*0.2))
                    elif direction == "down":
                        await asyncio.to_thread(driver.swipe, w//2, int(h*0.2), w//2, int(h*0.8))
                    elif direction == "left":
                        await asyncio.to_thread(driver.swipe, int(w*0.8), h//2, int(w*0.2), h//2)
                    elif direction == "right":    
                        await asyncio.to_thread(driver.swipe, int(w*0.2), h//2, int(w*0.8), h//2)
                except Exception as ex:
                    await queue.put({'type': 'error', 'text': f"Action failed: {str(ex)}"})
            else:
                await queue.put({'type': 'error', 'text': f"Unknown action: {action}"})
                break
            
            # Let the UI settle
            await asyncio.to_thread(driver.implicitly_wait, 2)
            await asyncio.sleep(2)
            
        else:
            await queue.put({'type': 'error', 'text': 'Task failed to complete within the maximum number of steps.'})

    except Exception as e:
        await queue.put({'type': 'error', 'text': f"Mobile Agent Error: {str(e)}\n{traceback.format_exc()}"})
    finally:
        if driver:
            try:
                await queue.put({'type': 'step', 'text': 'Closing Appium session and cleaning up...'})
                await asyncio.to_thread(driver.quit)
            except: pass
