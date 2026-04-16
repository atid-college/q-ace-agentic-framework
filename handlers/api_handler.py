import json
from typing import Dict, Any
from handlers.base_handler import BaseHandler
from tools.api_tool import APITool

class APIHandler(BaseHandler):
    """
    UI Handler for the User Management API Tool using Natural Language.
    """
    
    def __init__(self):
        self.tool_instance = APITool()

    @property
    def tool_id(self) -> str:
        return "api"

    @property
    def tool_name(self) -> str:
        return "REST API Agent"

    @property
    def icon(self) -> str:
        return "server"

    def get_ui_definition(self) -> Dict[str, Any]:
        return {
            "title": "REST API Agent",
            "description": "Interact with any REST endpoint using AI.",
            "components": [
                {
                     "type": "textarea",
                     "id": "prompt",
                     "label": "Agent Instruction",
                     "placeholder": "e.g., 'Show me the first post' or 'Create a user named John with email john@test.com'"
                 },
                 {
                     "type": "button",
                     "id": "execute_btn",
                     "label": "Execute with AI",
                     "action": "llm_execute",
                     "style": "bg-gradient-to-r from-indigo-500 to-purple-600"
                 }
            ]
        }
        
    async def _get_tool_kwargs_from_llm(self, user_prompt: str, provider: Any) -> Dict[str, Any]:
        """Uses the LLM to map a natural language prompt to the APITool's execute kwargs."""
        sys_prompt = f"""
You are an intelligent API assistant. Your job is to translate the user's request (which might be in Hebrew or English) into a strict JSON object that will be passed as `**kwargs` to a generic REST API execution tool.

The API tool supports the following description and actions:
{self.tool_instance.description}

You must return ONLY a valid JSON object. Do not include any markdown formatting (no backticks, no ```json), no explanations, and no text outside the JSON.
The JSON must have an 'action' key (which should always be 'make_request' in this case), 'http_method' key, and 'endpoint' key.
You may add a 'payload' key (dictionary) if the method implies data submission.

Example 1 (List all users):
{{"action": "make_request", "http_method": "GET", "endpoint": "/users"}}

Example 2 (Delete user 5):
{{"action": "make_request", "http_method": "DELETE", "endpoint": "/users/5"}}

Example 3 (Create user Sarah email s@example.com):
{{"action": "make_request", "http_method": "POST", "endpoint": "/users", "payload": {{"name": "Sarah", "email": "s@example.com"}}}}

Ensure you map the intent to the correct standard REST semantics.
CRITICAL RULES:
1. NEVER guess sub-paths or sub-resources using names or values (e.g., do NOT use /users/Wisokyburgh or /posts/my-title).
2. If the user asks for item(s) by a field that is NOT an ID (e.g., 'users in city X', 'posts with title Y'), you MUST fetch the entire collection (e.g., /users or /posts). The system will filter them later.
3. Only use sub-paths for IDs if explicitly known (e.g., /users/1).
4. Always use plural names (e.g., /users NOT /user).

Example: "Find users in Wisokyburgh" -> {{"action": "make_request", "http_method": "GET", "endpoint": "/users"}}
Example: "Check if Sara is a user" -> {{"action": "make_request", "http_method": "GET", "endpoint": "/users"}}

Common endpoints (JSONPlaceholder):
- GET /posts
- GET /posts/{{id}}
- GET /comments?postId=1
- POST /posts
- DELETE /posts/{{id}}
"""
        messages = [
            {"role": "system", "content": sys_prompt.strip()},
            {"role": "user", "content": f"User Request: {user_prompt}\nReturn ONLY the raw JSON object."}
        ]
        
        response = await provider.generate_response(messages)
        content = response["content"].strip()
        
        # Robust JSON extraction: find first '{' and last '}'
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            content = content[start:end+1]
            
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            # Fallback: if it failed, maybe it's just a raw error message
            raise Exception(f"AI response not in valid JSON format: {content[:100]}...") from e

    async def _evaluate_api_response(self, user_prompt: str, api_result: Dict[str, Any], provider: Any) -> Dict[str, Any]:
        """Uses the LLM to analyze the API response against the user's original request."""
        sys_prompt = f"""
You are an API verification assistant.
Analyze the API JSON data below.

CRITICAL: Search through the entire JSON, including nested objects (like address.city) and lists.

Return ONLY a JSON object:
1. "analysis": A direct answer to the user in their language (Hebrew/English). Confirm if you found the specific value they asked for.
2. "is_verified": true (if found), false (if not found), or null (if no verification was asked).

Rule: Return ONLY the JSON.
"""
        
        # We slice the data string to avoid context length issues if the API returns a massive list
        data_str = json.dumps(api_result, indent=2, ensure_ascii=False)
        if len(data_str) > 15000:
             data_str = data_str[:15000] + "\n... [DATA TRUNCATED] ..."

        user_message = f"User Request: {user_prompt}\n\nAPI Response Data:\n{data_str}\n\nReturn ONLY the raw JSON object."
        
        messages = [
            {"role": "system", "content": sys_prompt.strip()},
            {"role": "user", "content": user_message}
        ]
        
        response = await provider.generate_response(messages)
        content = response["content"].strip()
        
        # Robust JSON extraction
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            content = content[start:end+1]
            
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise Exception(f"AI evaluation not in valid JSON format: {content[:100]}...") from e

    async def handle_action(self, action: str, data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Routes the UI natural language action to the LLM, then to the APITool, and finally evaluates the response.
        """
        if action == "llm_execute":
            user_prompt = data.get("prompt")
            if not user_prompt:
                 return {"status": "error", "message": "A prompt is required."}
                 
            provider = context.get("provider") if context else None
            if not provider:
                 return {"status": "error", "message": "No active LLM provider found to process the request."}
                 
            try:
                # 1. Ask LLM to translate prompt to kwargs
                kwargs = await self._get_tool_kwargs_from_llm(user_prompt, provider)
            except Exception as e:
                return {"status": "error", "message": f"LLM Processing failed: {e}"}
                
            # 2. Execute the APITool using the generated kwargs + custom base_url
            server_url = data.get("server_url")
            if server_url:
                kwargs["base_url"] = server_url

            result = await self.tool_instance.execute(**kwargs)
            
            # Attach the LLM reasoning/kwargs to show what it attempted
            result["llm_intent"] = kwargs
            
            # 3. If the request was successful, have the LLM evaluate the result against the user's prompt
            if result.get("status") == "success":
                try:
                    eval_payload = result.get("data")
                    
                    # Conditional flattening for Ollama to help small models
                    provider_name = provider.__class__.__name__
                    if "Ollama" in provider_name:
                         eval_payload = self._flatten_data(eval_payload)

                    eval_data = await self._evaluate_api_response(user_prompt, eval_payload, provider)
                    result["ai_analysis"] = eval_data.get("analysis", "No text provided.")
                    result["is_verified"] = eval_data.get("is_verified")
                except Exception as e:
                    # Don't fail the whole request if analysis fails, just note it
                    result["ai_analysis"] = f"Failed to generate AI analysis: {e}"
                    result["is_verified"] = None
            
            return result


        return {"status": "error", "message": f"Unknown action: {action}"}

    def _flatten_data(self, data: Any, prefix: str = "") -> Dict[str, Any]:
        """Flattens nested dictionaries and lists for easier processing by small LLMs."""
        items = {}
        if isinstance(data, dict):
            for k, v in data.items():
                new_key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, (dict, list)):
                    items.update(self._flatten_data(v, new_key))
                else:
                    items[new_key] = v
        elif isinstance(data, list):
            for i, v in enumerate(data):
                new_key = f"{prefix}[{i}]"
                if isinstance(v, (dict, list)):
                    items.update(self._flatten_data(v, new_key))
                else:
                    items[new_key] = v
        else:
            items[prefix] = data
        return items
