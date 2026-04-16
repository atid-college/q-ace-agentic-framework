# Q-ACE: Agentic QA Framework

Modular AI Agent Engine for Quality Assurance tasks, built with FastAPI and modern LLM providers. Q-ACE transforms standard QA tools into intelligent agents capable of analysis, verification, and automated orchestration.

## 🚀 Key Features

- **Modular Architecture**: Clean separation between `core` orchestration, `handlers` for tool logic, `providers` for LLMs, and `tools` for low-level execution.
- **Role-Based Access Control (RBAC)**: Secure login system with `admin` and `tester` roles, managing permissions for specific tools and analytics.
- **AI-Powered Agents**:
    - **Browser Agent**: High-level web automation with real-time feedback and AI analysis.
    - **Database Agent**: Natural language query execution with AI verification of results.
    - **REST API Agent**: Intelligent interaction with REST endpoints to fetch, create, edit, and verify data using natural language prompts.
    - **Test Generator Agent**: Automated generation of comprehensive test cases (Functionality, Security, etc.) from specifications using advanced testing techniques.
    - **Mobile Agent**: AI-driven Android/iOS device automation via Appium, with natural language task execution, live UI hierarchy parsing, and persistent execution history.
- **Extended Tool Integration (Under Implementation)**:
    - Built-in placeholders for **Jenkins, GitHub Actions, Jira, Slack, Qase, Postman, and GitHub**.
- **LLM Provider Switching**: Support for Google Gemini, local Ollama, OpenAI, Anthropic, DeepSeek, and more.
- **Integrated Ollama Management**: Manage your local Ollama server (Start/Stop/Status) directly from the interface.
- **Modern UI**: A premium, responsive chat-based orchestration hub.

## 🛠️ Project Structure

- `core/`: Orchestrator, Context Management, Tool Registry, Auth Utilities, and LLM Client.
- `handlers/`: Logic layer for tools (SQLite, API, Spec Analyzer, Browser, and placeholders).
- `providers/`: LLM provider implementations (Gemini, Ollama).
- `tools/`: Low-level execution plugins.
- `static/`: Modern HTML/JS frontend (Alpine.js, TailwindCSS).
- `data/`: SQLite databases (`q-ace.db`), test specs, **Browser Agent documentation/history**, and **Mobile Agent documentation/history**.
- `main.py`: FastAPI application entry point.

## 🚦 Quick Start

### 1. Prerequisites
- Python 3.9+
- [Ollama](https://ollama.com/) (for local LLM support)
- Google API Key (for Gemini support)

### 2. Automatic Setup

First, clone the repository and navigate into it:

```bash
git clone https://github.com/atid-college/q-ace-framework.git
cd q-ace-framework
```

Then, simply run the provided installer. It will handle virtual environments (including the specialized Browser Agent `.venv`), dependencies, and database initialization:

**Windows**:
```batch
win-install.bat
```

**MacOS / Linux**:
```bash
chmod +x mac-install.sh
./mac-install.sh
```

### 3. Run the Server
For the next times, simply launch the framework using the run script:

**Windows**:
```batch
win-run.bat
```

**MacOS / Linux**:
```bash
chmod +x mac-run.sh
./mac-run.sh
```
Open `http://localhost:8090` in your browser.

## 🌐 Specialized Documentation
- [Browser Agent Guide](data/browser-agent-docs/README.md): Setup, configuration, and automation features.
- [Database Agent Guide](data/database-agent-docs/README.md): Text-to-SQL, sample databases, and verification.
- [REST API Agent Guide](data/api-agent-docs/README.md): Natural language API interaction and analysis.
- [Test Generator Agent Guide](data/test-gen-agent-docs/README.md): Specification analysis and test case generation.
- [Mobile Agent Guide](data/mobile-agent-docs/README.md): Appium setup, device configuration, AI-driven mobile automation, and history analytics.

## 🔐 Authentication & Roles

The framework uses JWT-based authentication. The installer automatically sets up the initial database.

**Initial Credentials**:
- **Username**: `admin`
- **Password**: `admin123`

> [!IMPORTANT]
> It is highly recommended to change your password after the first login. You can do this in the dashboard under **User Management**.

### User Roles:
- **Admin**: Full access to all tools and administrative analytics.
- **Tester**: Access limited to assigned tools (e.g., API, SQLite).

## 🧪 Extending the Framework

### Adding a Handler
Handlers manage the high-level logic and UI definition for a tool. Create a new file in `handlers/` inheriting from `BaseHandler`.

### Adding a Tool
Tools provide the execution layer (e.g., making the actual HTTP request). Create a new file in `tools/` inheriting from `BaseTool`.

```python
from core.base_tool import BaseTool

class CustomTool(BaseTool):
    @property
    def name(self): return "custom_tool"
    
    async def execute(self, **kwargs):
        return {"status": "success", "data": "..."}
```

## 🤝 Contributing & Community

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) to get started.
All participants are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

---
Built with ❤️ by <a href="https://atidcollege.co.il" target="_blank">**ATID College**</a>