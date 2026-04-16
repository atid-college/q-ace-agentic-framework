import sqlite3
import os
import asyncio
from typing import Dict, Any, List, Optional
from core.auth_utils import hash_password, verify_password, create_access_token
from handlers.base_handler import BaseHandler

class AuthHandler(BaseHandler):
    """
    Handler for Authentication and Admin Management logic.
    """
    DB_PATH = "data/q-ace.db"

    def __init__(self):
        # Database should already be initialized by init_auth_db.py
        pass

    @property
    def tool_id(self) -> str:
        return "auth"

    @property
    def tool_name(self) -> str:
        return "Authentication"

    @property
    def icon(self) -> str:
        return "lock"

    def get_ui_definition(self) -> Dict[str, Any]:
        # This handler doesn't have a direct tool UI for general users,
        # but it provides endpoints for the admin dashboard and login.
        return {
            "title": "Auth & Management",
            "description": "System administration and security.",
            "components": []
        }

    async def handle_action(self, action: str, data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        if action == "login":
            username = data.get("username")
            password = data.get("password")
            
            if not username or not password:
                return {"status": "error", "message": "Username and password required"}
                
            def _do_login():
                conn = sqlite3.connect(self.DB_PATH)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                user = cursor.fetchone()
                
                if user and verify_password(password, user["password_hash"]):
                    # Update last login
                    cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user["id"],))
                    
                    # Get group permissions (deduplicated)
                    cursor.execute("SELECT DISTINCT tool_id FROM permissions WHERE group_id = ?", (user["group_id"],))
                    tools = list(dict.fromkeys(row[0] for row in cursor.fetchall()))

                    
                    # Get group name
                    cursor.execute("SELECT name FROM groups WHERE id = ?", (user["group_id"],))
                    group_name = cursor.fetchone()[0]
                    
                    token = create_access_token({
                        "sub": user["username"],
                        "user_id": user["id"],
                        "role": user["role"],
                        "group_id": user["group_id"],
                        "group_name": group_name,
                        "permissions": tools
                    })
                    
                    conn.commit()
                    conn.close()
                    return {
                        "status": "success",
                        "token": token,
                        "user": {
                            "username": user["username"],
                            "role": user["role"],
                            "group_name": group_name,
                            "permissions": tools
                        }
                    }
                
                conn.close()
                return {"status": "error", "message": "Invalid username or password"}

            return await asyncio.to_thread(_do_login)

        elif action == "get_analytics":
            # Admin only
            if context.get("role") != "admin":
                 return {"status": "error", "message": "Permission denied"}
                 
            def _get_analytics():
                conn = sqlite3.connect(self.DB_PATH)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Simulated analytics data for now
                # In real system, we would query the 'analytics' table
                cursor.execute("SELECT count(*) as count, tool_id FROM analytics GROUP BY tool_id")
                activity = [dict(row) for row in cursor.fetchall()]
                
                # More mock data for the dashboard
                analytics_data = {
                    "total_users": 12,
                    "active_today": 4,
                    "top_tools": [
                        {"name": "Text-to-SQL", "score": 85},
                        {"name": "REST API Client", "score": 72},
                        {"name": "Spec Analyzer", "score": 45}
                    ],
                    "usage_by_group": [
                        {"group": "QA Core", "value": 65},
                        {"group": "QA BI", "value": 25},
                        {"group": "QA Design", "value": 10}
                    ]
                }
                conn.close()
                return {"status": "success", "analytics": analytics_data}
            
            return await asyncio.to_thread(_get_analytics)

        elif action == "create_user":
            # Admin only
            if context.get("role") != "admin":
                 return {"status": "error", "message": "Permission denied"}
            
            username = data.get("username")
            password = data.get("password")
            role = data.get("role", "user")
            group_id = data.get("group_id")
            
            if not username or not password or not group_id:
                 return {"status": "error", "message": "Missing required fields"}
                 
            conn = sqlite3.connect(self.DB_PATH)
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO users (username, password_hash, role, group_id) VALUES (?, ?, ?, ?)",
                               (username, hash_password(password), role, group_id))
                conn.commit()
                return {"status": "success", "message": f"User {username} created"}
            except sqlite3.IntegrityError:
                return {"status": "error", "message": "Username already exists"}
            finally:
                conn.close()

        elif action == "get_users":
            if context.get("role") != "admin": return {"status": "error", "message": "Denied"}
            conn = sqlite3.connect(self.DB_PATH); conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT u.id, u.username, u.role, u.group_id, g.name as group_name FROM users u LEFT JOIN groups g ON u.group_id = g.id")
            users = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return {"status": "success", "users": users}

        elif action == "update_user":
            if context.get("role") != "admin": return {"status": "error", "message": "Denied"}
            user_id = data.get("id")
            role = data.get("role")
            group_id = data.get("group_id")
            password = data.get("password")
            
            conn = sqlite3.connect(self.DB_PATH); cursor = conn.cursor()
            try:
                if password:
                    cursor.execute("UPDATE users SET role = ?, group_id = ?, password_hash = ? WHERE id = ?",
                                   (role, group_id, hash_password(password), user_id))
                else:
                    cursor.execute("UPDATE users SET role = ?, group_id = ? WHERE id = ?",
                                   (role, group_id, user_id))
                conn.commit()
                return {"status": "success", "message": "User updated"}
            except Exception as e: return {"status": "error", "message": str(e)}
            finally: conn.close()

        elif action == "delete_user":
            if context.get("role") != "admin": return {"status": "error", "message": "Denied"}
            if data.get("id") == context.get("user_id"): return {"status": "error", "message": "Self-delete forbidden"}
            conn = sqlite3.connect(self.DB_PATH); cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (data.get("id"),))
            conn.commit(); conn.close()
            return {"status": "success", "message": "User deleted"}

        elif action == "get_groups":
            if context.get("role") != "admin": return {"status": "error", "message": "Denied"}
            conn = sqlite3.connect(self.DB_PATH); conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM groups")
            groups = [dict(row) for row in cursor.fetchall()]
            for g in groups:
                cursor.execute("SELECT tool_id FROM permissions WHERE group_id = ?", (g["id"],))
                g["tools"] = [r[0] for r in cursor.fetchall()]
            conn.close()
            return {"status": "success", "groups": groups}

        elif action == "create_group":
            if context.get("role") != "admin": return {"status": "error", "message": "Denied"}
            conn = sqlite3.connect(self.DB_PATH); cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO groups (name, description) VALUES (?, ?)", (data.get("name"), data.get("description")))
                gid = cursor.lastrowid
                for t in data.get("tools", []): cursor.execute("INSERT INTO permissions (group_id, tool_id) VALUES (?, ?)", (gid, t))
                conn.commit()
                return {"status": "success", "message": "Group created"}
            except Exception as e: return {"status": "error", "message": str(e)}
            finally: conn.close()

        elif action == "update_group":
            if context.get("role") != "admin": return {"status": "error", "message": "Denied"}
            group_id = data.get("id")
            conn = sqlite3.connect(self.DB_PATH); cursor = conn.cursor()
            try:
                cursor.execute("UPDATE groups SET name = ?, description = ? WHERE id = ?", 
                               (data.get("name"), data.get("description"), group_id))
                cursor.execute("DELETE FROM permissions WHERE group_id = ?", (group_id,))
                for t in data.get("tools", []):
                    cursor.execute("INSERT INTO permissions (group_id, tool_id) VALUES (?, ?)", (group_id, t))
                conn.commit()
                return {"status": "success", "message": "Group updated"}
            except Exception as e: return {"status": "error", "message": str(e)}
            finally: conn.close()

        elif action == "delete_group":
            if context.get("role") != "admin": return {"status": "error", "message": "Denied"}
            conn = sqlite3.connect(self.DB_PATH); cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM users WHERE group_id = ?", (data.get("id"),))
            if cursor.fetchone()[0] > 0: conn.close(); return {"status": "error", "message": "Group has users"}
            cursor.execute("DELETE FROM permissions WHERE group_id = ?", (data.get("id"),))
            cursor.execute("DELETE FROM groups WHERE id = ?", (data.get("id"),))
            conn.commit(); conn.close()
            return {"status": "success", "message": "Group deleted"}

        return {"status": "error", "message": f"Unknown action: {action}"}
