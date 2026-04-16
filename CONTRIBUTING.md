# Contributing to Q-Ace Agentic Framework 🚀

First off, thank you for considering contributing to Q-Ace! It's people like you who make Q-Ace such a powerful tool for the QA community.

## How Can I Contribute?

### 🛠️ Developing New Agents
Q-Ace is built on a modular architecture. You can contribute by building new Handlers or Tools:
- **Handlers**: Manage high-level logic and UI definitions (located in `handlers/`).
- **Tools**: Provide the execution layer, such as API calls or DB interactions (located in `tools/`).

### 🐛 Reporting Bugs
- Use the GitHub Issues dependencies to report bugs.
- Include steps to reproduce, the environment (Windows/Linux), and the LLM provider used (e.g., Gemini, Ollama).

### 💡 Feature Requests
We are looking to expand our ecosystem with agents for Jenkins, Jira, Slack, and more. If you have an idea, open an issue to discuss it!

## Pull Request Process
1. Fork the repository and create your branch from `main`.
2. If you've added an agent, ensure you include a `README.md` in the relevant data folder.
3. Ensure your code follows the existing structure (FastAPI for backend, Alpine.js/Tailwind for frontend).
4. Submit your PR with a clear description of the changes.

## Development Setup
- Follow the `install.bat` process to set up your local environment.
- For Mobile Agent contributions, ensure Appium and Android drivers are configured.

Thank you for helping us build the future of Agentic QA!