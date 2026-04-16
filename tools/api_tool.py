import requests
from typing import Any, Dict, Optional
from core.base_tool import BaseTool

class APITool(BaseTool):
    """
    A tool to manage users via a REST API.
    """
    
    def __init__(self, base_url: str = "https://jsonplaceholder.typicode.com"):
        self.base_url = base_url

    @property
    def name(self) -> str:
        return "api_tool"

    @property
    def description(self) -> str:
        return (
            "A powerful, generic REST API client tool. "
            "Supported action: 'make_request'.\n"
            "This action executes an HTTP request against any valid endpoint.\n"
            "Arguments required for 'make_request':\n"
            "- 'http_method': The HTTP verb (e.g., 'GET', 'POST', 'DELETE', 'PUT', 'PATCH').\n"
            "- 'endpoint': The target URI path starting with a slash (e.g., '/users', '/posts/1', '/comments?postId=1').\n"
            "- 'payload': (Optional) A dictionary containing the JSON body for the request (relevant for POST/PUT/PATCH)."
        )

    async def execute(self, **kwargs) -> Any:
        action = kwargs.get("action")
        
        if action != "make_request":
            return {"status": "error", "message": f"Verification failed: Unsupported action '{action}'. Only 'make_request' is valid."}
            
        http_method = kwargs.get("http_method")
        endpoint = kwargs.get("endpoint")
        payload = kwargs.get("payload")
        
        if not http_method or not endpoint:
             return {"status": "error", "message": "Verification failed: 'http_method' and 'endpoint' are strictly required."}
             
        base_url = kwargs.get("base_url") or self.base_url
        return self.make_request(http_method, endpoint, payload, base_url=base_url)

    def make_request(self, http_method: str, endpoint: str, payload: Optional[Dict[str, Any]] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
        """Performs a generic HTTP request dynamically based on the provided method and endpoint."""
        target_base = base_url or self.base_url
        url = f"{target_base.rstrip('/')}/{endpoint.lstrip('/')}"
        
        try:
            # Map standard verbs to requests library methods dynamically
            method_func = getattr(requests, http_method.lower(), None)
            if not method_func:
                return {"status": "error", "message": f"Verification failed: Invalid HTTP method '{http_method}'"}
                
            response = method_func(url, json=payload, timeout=10)
            
            # Read content regardless of success, since APIs often return error reasoning
            try:
                response_data = response.json()
            except ValueError:
                response_data = response.text
                
            if response.status_code >= 400:
                msg = f"API Error {response.status_code}"
                if response.status_code == 404:
                    msg = f"API 404 Error: Endpoint '{http_method} {endpoint}' not found."
                return {
                    "status": "error", 
                    "message": msg,
                    "data": response_data,
                    "url": url
                }
                
            return {
                "status": "success", 
                "message": f"Request to {url} completed successfully.", 
                "data": response_data,
                "status_code": response.status_code
            }
            
        except requests.exceptions.Timeout:
            return {"status": "error", "message": f"Execution failed: Connection to {url} timed out."}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": f"Execution failed: API request error: {str(e)}"}
        except Exception as e:
             return {"status": "error", "message": f"Execution failed: An unexpected error occurred: {str(e)}"}
