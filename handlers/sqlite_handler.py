import sqlite3
import os
import shutil
import json
import asyncio
from typing import Dict, Any, List, Optional
from handlers.base_handler import BaseHandler

class SQLiteHandler(BaseHandler):
    """
    Enhanced Handler for SQLite: Text-to-SQL, Sample DBs, and Reset functionality.
    """
    
    TEMPLATES_DIR = "templates"
    ACTIVE_DB_DIR = "data/database-agent-db"

    def __init__(self):
        # Ensure directories exist
        os.makedirs(self.TEMPLATES_DIR, exist_ok=True)
        os.makedirs(self.ACTIVE_DB_DIR, exist_ok=True)

    @property
    def tool_id(self) -> str:
        return "sqlite"

    @property
    def tool_name(self) -> str:
        return "Database Agent"

    @property
    def icon(self) -> str:
        return "database"

    def get_ui_definition(self) -> Dict[str, Any]:
        return {
            "title": "Database Agent",
            "description": "Connect to an SQLite DB and ask questions in plain English.",
            "components": [
                {
                    "type": "dropdown",
                    "id": "sample_db",
                    "label": "Sample Databases",
                    "options": [
                        {"label": "Custom Path", "value": "custom"},
                        {"label": "Chinook (Music Store)", "value": "chinook.db"},
                        {"label": "Northwind (Trading)", "value": "northwind.db"},
                        {"label": "QA Test (Simple)", "value": "qa_test.db"}
                    ]
                },
                {
                    "type": "input",
                    "id": "db_path",
                    "label": "Custom SQLite Path",
                    "placeholder": "e.g., ./data/test.db"
                },
                {
                    "type": "textarea",
                    "id": "prompt",
                    "label": "Natural Language Query",
                    "placeholder": "e.g., 'Show me the top 5 customers by revenue'"
                },
                {
                    "type": "button",
                    "id": "generate_btn",
                    "label": "Execute with AI",
                    "action": "text_to_sql",
                    "style": "bg-gradient-to-r from-emerald-500 to-teal-600"
                },
                {
                    "type": "button",
                    "id": "reset_btn",
                    "label": "Reset Database",
                    "action": "reset_db",
                    "style": "bg-slate-100 text-slate-600 border border-slate-200"
                }
            ]
        }

    async def _get_schema(self, db_path: str) -> str:
        """Extracts table names and column info from sqlite_master in a separate thread."""
        def _do_get():
            import os
            # Ensure path is absolute for reliability
            full_path = os.path.abspath(db_path)
            if not os.path.exists(full_path):
                return f"Error: Database file not found at {full_path} (Original: {db_path})"
                
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Fetch table schemas
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
                schemas = [row[0] for row in cursor.fetchall() if row[0]]
                
                conn.close()
                return "\n".join(schemas)
            except Exception as e:
                return f"Error extracting schema: {e}"
        return await asyncio.to_thread(_do_get)

    async def _get_sql_query(self, user_prompt: str, schema: str, provider: Any) -> str:
        """Asks the LLM to generate SQL based on prompt and schema."""
        prompt = f"""
        You are an expert SQL assistant. Given the following SQLite schema, generate a valid SELECT query for the user's request.
        Return ONLY the raw SQL query. No markdown formatting, no explanations.
        
        SCHEMA:
        {schema}
        
        USER REQUEST:
        {user_prompt}
        """
        
        response = await provider.generate_response([{"role": "user", "content": prompt}])
        sql = response["content"].strip()
        
        # Clean up possible markdown artifacts
        if sql.startswith("```sql"):
            sql = sql[6:].split("```")[0].strip()
        elif sql.startswith("```"):
            sql = sql[3:].split("```")[0].strip()
            
        return sql

    async def _evaluate_sql_response(self, user_prompt: str, results: List[Dict[str, Any]], provider: Any) -> Dict[str, Any]:
        """Uses the LLM to analyze the SQL query results against the user's original request."""
        sys_prompt = f"""
        You are an intelligent data verification assistant.
        Your task is to analyze the JSON data returned by a SQL query and provide a verification based on the user's original request (which might be in Hebrew or English).

        You must return a strict JSON object with EXACTLY two keys:
        1. "analysis": A concise, direct, natural language answer or explanation in the same language as the user's request. Do not describe the JSON structure itself.
        2. "is_verified": A boolean flag. 
           - Set to `true` if the user asked to verify something AND it successfully matched/passed.
           - Set to `false` if the user asked to verify something AND it failed/didn't match.
           - Set to `null` if the user just asked a question, requested data, or didn't explicitly ask for a verification.

        Do not include any markdown formatting (no backticks, no ```json). Return ONLY valid JSON.
        """
        
        # We slice the data string to avoid context length issues if the query returns a massive list
        data_str = json.dumps(results, indent=2, ensure_ascii=False)
        if len(data_str) > 15000:
             data_str = data_str[:15000] + "\n... [DATA TRUNCATED] ..."

        user_message = f"User Request: {user_prompt}\n\nSQL Results Data:\n{data_str}\n\nReturn ONLY the raw JSON object."
        
        messages = [
            {"role": "system", "content": sys_prompt.strip()},
            {"role": "user", "content": user_message}
        ]
        
        print(f"[DEBUG] Prompting AI for evaluation with {len(results)} rows...")
        response = await provider.generate_response(messages)
        content = response["content"].strip()
        print(f"[DEBUG] AI Evaluation response received: {content[:100]}...")
        
        # Clean up possible markdown artifacts
        if content.startswith("```json"):
            content = content[7:].split("```")[0].strip()
        elif content.startswith("```"):
            content = content[3:].split("```")[0].strip()
            
        try:
            return json.loads(content)
        except Exception as e:
            raise Exception(f"Failed to parse AI evaluation JSON response: {content}") from e

    async def handle_action(self, action: str, data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        queue = context.get("queue") if context else None
        step_id = context.get("step_id") if context else None

        async def emit_progress(msg):
            if queue and step_id:
                await queue.put({"type": "tool_progress", "step_id": step_id, "text": msg})

        if action == "text_to_sql":
            db_path = data.get("db_path")
            sample_db = data.get("sample_db")
            
            # Resolve path if sample selected
            if sample_db and sample_db != "custom":
                db_path = os.path.join(self.ACTIVE_DB_DIR, sample_db)

            user_prompt = data.get("prompt")
            provider = context.get("provider") if context else None
            
            if not db_path or not user_prompt:
                return {"status": "error", "message": f"Missing DB path or prompt. Path: '{db_path}'"}
            
            if not provider:
                return {"status": "error", "message": "No active LLM provider found"}

            await emit_progress(f"Reading schema from {os.path.basename(db_path)}...")
            schema = await self._get_schema(db_path)
            if "Error" in schema:
                return {"status": "error", "message": schema}

            try:
                await emit_progress("Generating optimized SQL query...")
                sql = await self._get_sql_query(user_prompt, schema, provider)
            except Exception as e:
                return {"status": "error", "message": f"LLM Generation failed: {e}"}

            if not sql.lower().strip().startswith("select"):
                 return {
                     "status": "warning", 
                     "message": "Execution blocked: For safety, only SELECT queries are allowed in this tool.",
                     "query": sql
                 }

            try:
                def _do_execute():
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute(sql)
                    rows = cursor.fetchall()
                    results = [dict(row) for row in rows]
                    conn.close()
                    return results

                results = await asyncio.to_thread(_do_execute)
                
                output = {
                    "status": "success",
                    "query": sql,
                    "data": results,
                    "count": len(results),
                    "active_db": db_path
                }

                # NEW: Call AI evaluation
                try:
                    await emit_progress(f"AI Analysis: Slicing {len(results)} rows for evaluation...")
                    eval_data = await self._evaluate_sql_response(user_prompt, results, provider)
                    await emit_progress("AI Analysis: Summarizing findings...")
                    output["ai_analysis"] = eval_data.get("analysis", "No analysis provided.")
                    output["is_verified"] = eval_data.get("is_verified")
                    await emit_progress("AI Analysis: Complete.")
                except Exception as eval_err:
                    await emit_progress(f"AI Analysis: Failed ({eval_err})")
                    output["ai_analysis"] = f"AI Evaluation failed: {eval_err}"
                    output["is_verified"] = None

                return output

            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Database execution error: {e}",
                    "query": sql
                }

        elif action == "reset_db":
            sample_db = data.get("sample_db")
            if not sample_db or sample_db == "custom":
                return {"status": "error", "message": "Please select a sample database to reset."}
            
            src = os.path.join(self.TEMPLATES_DIR, sample_db)
            dst = os.path.join(self.ACTIVE_DB_DIR, sample_db)
            
            if not os.path.exists(src):
                # For this scaffold, if template doesn't exist, create an empty one
                try:
                    conn = sqlite3.connect(src)
                    conn.execute("CREATE TABLE info (message TEXT)")
                    conn.execute("INSERT INTO info VALUES ('Template created automatically.')")
                    conn.commit()
                    conn.close()
                except:
                    pass

            try:
                shutil.copy2(src, dst)
                return {"status": "success", "message": f"Database {sample_db} has been reset from template."}
            except Exception as e:
                return {"status": "error", "message": f"Failed to reset database: {e}"}
        
        elif action == "get_schema":
            sample_db = data.get("sample_db")
            db_path = data.get("db_path")

            if sample_db and sample_db != "custom":
                db_path = os.path.join(self.ACTIVE_DB_DIR, sample_db)

            if not db_path:
                return {"status": "error", "message": "No database selected."}

            if not os.path.exists(db_path):
                return {"status": "error", "message": f"Database file not found: {db_path}"}

            try:
                def _read_schema():
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()

                    # Get all table names
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
                    tables = [row[0] for row in cursor.fetchall()]

                    schema_list = []
                    for table in tables:
                        cursor.execute(f"PRAGMA table_info(\"{table}\");")
                        cols = cursor.fetchall()
                        schema_list.append({
                            "table": table,
                            "columns": [
                                {
                                    "name": col[1],
                                    "type": col[2],
                                    "notnull": bool(col[3]),
                                    "pk": bool(col[5])
                                }
                                for col in cols
                            ]
                        })

                    conn.close()
                    return {"status": "success", "schema": schema_list, "table_count": len(tables)}
                
                return await asyncio.to_thread(_read_schema)
            except Exception as e:
                return {"status": "error", "message": f"Failed to read schema: {e}"}

        return {"status": "error", "message": f"Unknown action: {action}"}
