import os
import json
import httpx
import asyncio
from typing import Dict, Any, List, Optional
from handlers.base_handler import BaseHandler
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import pypdf

class SpecAnalyzerHandler(BaseHandler):
    """
    Handler for Spec-to-Test Generator: Analyzes documents or URLs to generate test cases.
    """
    
    SPEC_DATA_DIR = "data/test_specs"
    GENERATED_TESTS_DIR = "data/generated_tests"

    def __init__(self):
        # Ensure directories exist
        os.makedirs(self.SPEC_DATA_DIR, exist_ok=True)
        os.makedirs(self.GENERATED_TESTS_DIR, exist_ok=True)

    @property
    def tool_id(self) -> str:
        return "spec_analyzer"

    @property
    def tool_name(self) -> str:
        return "Test Gen Agent"

    @property
    def icon(self) -> str:
        return "file-text"

    def get_ui_definition(self) -> Dict[str, Any]:
        return {
            "title": "Test Gen Agent",
            "description": "Analyze specification documents or URLs to generate comprehensive test cases.",
            "components": [
                {
                    "type": "dropdown",
                    "id": "spec_file",
                    "label": "Select Existing Spec",
                    "options": [
                        {"label": "Manual Path / URL", "value": "custom"}
                    ]
                },
                {
                    "type": "input",
                    "id": "custom_path",
                    "label": "Custom File Path or URL",
                    "placeholder": "e.g., C:/docs/spec.pdf or https://example.com/spec"
                },
                {
                    "type": "dropdown",
                    "id": "category",
                    "label": "Test Category",
                    "options": [
                        {"label": "Functionality", "value": "functionality"},
                        {"label": "Security", "value": "security"},
                        {"label": "Performance", "value": "performance"},
                        {"label": "Accessibility", "value": "accessibility"},
                        {"label": "Usability", "value": "usability"},
                        {"label": "Reliability", "value": "reliability"}
                    ]
                },
                {
                    "type": "checkbox_group",
                    "id": "techniques",
                    "label": "Testing Techniques",
                    "options": [
                        {"label": "Edge Cases", "value": "edge_cases"},
                        {"label": "Boundary Value Analysis", "value": "bva"},
                        {"label": "Equivalence Partitioning", "value": "ep"},
                        {"label": "Decision Table Testing", "value": "decision_table"},
                        {"label": "State Transition Testing", "value": "state_transition"},
                        {"label": "Smoke Testing", "value": "smoke"},
                        {"label": "Positive/Negative Testing", "value": "positive_negative"},
                        {"label": "Pair-wise Testing", "value": "pairwise"}
                    ]
                },
                {
                    "type": "button",
                    "id": "generate_tests_btn",
                    "label": "Generate Test Cases",
                    "action": "analyze_spec",
                    "style": "bg-gradient-to-r from-blue-500 to-indigo-600"
                }
            ]
        }

    async def _read_file_content(self, path: str) -> str:
        """Reads content from various file types in a separate thread."""
        def _do_read():
            ext = os.path.splitext(path)[1].lower()
            if ext == ".pdf":
                reader = pypdf.PdfReader(path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
            elif ext == ".json":
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return json.dumps(data, indent=2)
            else: # .txt, .md, etc.
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
        return await asyncio.to_thread(_do_read)

    async def _scrape_url(self, url: str) -> str:
        """Scrapes a URL and converts to Markdown."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            html_content = response.text
            
            # Simple BeautifulSoup + Markdownify fallback
            soup = BeautifulSoup(html_content, 'html.parser')
            # Remove scripts and styles
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = md(str(soup))
            return text

    async def handle_action(self, action: str, data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        if action == "get_spec_files":
            files = os.listdir(self.SPEC_DATA_DIR)
            options = [{"label": "Manual Path / URL", "value": "custom"}]
            for f in files:
                options.append({"label": f, "value": f})
            return {"status": "success", "options": options}

        elif action == "analyze_spec":
            spec_file = data.get("spec_file")
            custom_path = data.get("custom_path")
            category = data.get("category", "functionality")
            techniques = data.get("techniques", [])
            provider = context.get("provider") if context else None

            if not provider:
                return {"status": "error", "message": "No active LLM provider found"}

            content = ""
            source_name = ""

            try:
                if spec_file and spec_file != "custom":
                    path = os.path.join(self.SPEC_DATA_DIR, spec_file)
                    content = await self._read_file_content(path)
                    source_name = spec_file
                elif custom_path:
                    if custom_path.startswith("http"):
                        content = await self._scrape_url(custom_path)
                        source_name = "URL_Scrape"
                    else:
                        content = await self._read_file_content(custom_path)
                        source_name = os.path.basename(custom_path)
                else:
                    return {"status": "error", "message": "No specification provided"}

                if not content.strip():
                    return {"status": "error", "message": "Failed to extract content from specification"}

                # Call LLM
                prompt = self._build_analysis_prompt(content, category, techniques)
                response = await provider.generate_response([{"role": "user", "content": prompt}])
                test_cases_md = response["content"].strip()

                # Save results
                safe_source = source_name.replace(".", "_").replace("/", "_").replace("\\", "_")
                result_filename = f"tests_{safe_source}_{category}.md"
                result_path = os.path.join(self.GENERATED_TESTS_DIR, result_filename)
                def _do_write():
                    with open(result_path, 'w', encoding='utf-8') as f:
                        f.write(test_cases_md)
                await asyncio.to_thread(_do_write)

                return {
                    "status": "success",
                    "test_cases": test_cases_md,
                    "filename": result_filename,
                    "category": category,
                    "techniques": techniques
                }

            except Exception as e:
                return {"status": "error", "message": f"Analysis failed: {str(e)}"}

        elif action == "save_to_local":
            filename = data.get("filename")
            content = data.get("content")
            if not filename or not content:
                # Fallback if filename not provided (e.g. from Custom Path)
                source = data.get("source_name", "custom")
                category = data.get("category", "all")
                safe_source = source.replace(".", "_").replace("/", "_").replace("\\", "_")
                filename = f"tests_{safe_source}_{category}.md"

            result_path = os.path.join(self.GENERATED_TESTS_DIR, filename)
            try:
                with open(result_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return {"status": "success", "message": f"Saved as {filename}", "filename": filename}
            except Exception as e:
                return {"status": "error", "message": f"Failed to save: {str(e)}"}

        elif action == "get_saved_tests":
            try:
                files = os.listdir(self.GENERATED_TESTS_DIR)
                tests = []
                for f in files:
                    if f.endswith(".md"):
                        path = os.path.join(self.GENERATED_TESTS_DIR, f)
                        mtime = os.path.getmtime(path)
                        tests.append({
                            "filename": f,
                            "timestamp": mtime,
                            "path": path
                        })
                # Sort by timestamp decending
                tests.sort(key=lambda x: x["timestamp"], reverse=True)
                return {"status": "success", "tests": tests}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "get_test_content":
            filename = data.get("filename")
            if not filename:
                return {"status": "error", "message": "Missing filename"}
            try:
                path = os.path.join(self.GENERATED_TESTS_DIR, filename)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {"status": "success", "content": content}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "delete_test":
            filename = data.get("filename")
            if not filename:
                return {"status": "error", "message": "Missing filename"}
            try:
                path = os.path.join(self.GENERATED_TESTS_DIR, filename)
                if os.path.exists(path):
                    os.remove(path)
                    return {"status": "success", "message": f"Deleted {filename}"}
                else:
                    return {"status": "error", "message": "File not found"}
            except Exception as e:
                return {"status": "error", "message": f"Failed to delete: {str(e)}"}

        return {"status": "error", "message": f"Unknown action: {action}"}

    def _build_analysis_prompt(self, content: str, category: str, techniques: List[str]) -> str:
        techniques_str = ", ".join(techniques) if techniques else "Standard QA Best Practices"
        prompt = f"""
You are an expert QA Engineer. Your task is to analyze the following specification content and generate a comprehensive suite of test cases.

TEST CATEGORY: {category.upper()}
APPLIED TECHNIQUES: {techniques_str}

Please generate the test cases in a clear Markdown table format with the following columns:
- ID
- Title
- Description
- Prerequisites
- Steps
- Expected Result
- Priority (High/Medium/Low)
- Technique (Which specific testing technique was applied)

If you identify any ambiguities or gaps in the specification, please list them in a "Potential Issues/Gaps" section after the table.

SPECIFICATION CONTENT:
---
{content}
---

Provide the response in the same language as the specification where appropriate (e.g., if the spec is in Hebrew, the test descriptions should be in Hebrew).
"""
        return prompt
