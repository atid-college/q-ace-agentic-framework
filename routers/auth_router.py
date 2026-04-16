"""
Authentication and admin endpoints.
Routes: /api/auth/login, /api/admin/analytics, /api/tools, /api/tool/action
"""

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from typing import Dict, Any

from routers.dependencies import get_current_user, _get_user_config, handlers
from core.llm_client import LLMClient

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class ActionRequest(BaseModel):
    tool_id: str
    action: str
    data: Dict[str, Any]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/api/auth/login")
async def login(request: LoginRequest, response: Response):
    """Login endpoint."""
    handler = handlers.get("auth")
    result = await handler.handle_action("login", request.dict())

    if result.get("status") == "error":
        raise HTTPException(status_code=401, detail=result.get("message"))

    token = result.pop("token", None)
    if token:
        response.set_cookie(
            key="q_ace_token",
            value=token,
            httponly=True,
            max_age=3600,
            samesite="lax",
            path="/",
            secure=False
        )
    return result


@router.get("/api/auth/me")
async def get_me(request: Request):
    """Get current user from cookie."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"status": "success", "user": user}

@router.post("/api/auth/logout")
async def logout(response: Response):
    """Clear the auth cookie."""
    response.delete_cookie("q_ace_token", path="/")
    return {"status": "success", "message": "Logged out"}


@router.get("/api/admin/analytics")
async def get_analytics(request: Request):
    """Admin analytics endpoint."""
    user = get_current_user(request)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    handler = handlers.get("auth")
    return await handler.handle_action("get_analytics", {}, context=user)


@router.get("/api/tools")
def list_tools(request: Request):
    """Lists available tools, filtered by user permissions."""
    user = get_current_user(request)
    if not user:
        return []

    permissions = user.get("permissions", [])

    return [
        {
            "id": h.tool_id,
            "name": h.tool_name,
            "icon": h.icon,
            "ui": h.get_ui_definition(),
        }
        for h in handlers.values()
        if h.tool_id in permissions or user.get("role") == "admin"
    ]


@router.post("/api/tool/action")
async def tool_action(request: ActionRequest, req: Request):
    """Generic endpoint for tool-specific actions."""
    user = get_current_user(req)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    permissions = user.get("permissions", [])
    if request.tool_id not in permissions and user.get("role") != "admin" and request.tool_id != "auth":
        raise HTTPException(status_code=403, detail="Forbidden: No permission for this tool")

    handler = handlers.get(request.tool_id)
    if not handler:
        raise HTTPException(status_code=404, detail="Tool handler not found")

    try:
        cfg = _get_user_config(req)
        provider = LLMClient.get_provider(cfg)
        result = await handler.handle_action(
            request.action,
            request.data,
            context={"provider": provider, "user_id": user.get("user_id"), "role": user.get("role")},
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
