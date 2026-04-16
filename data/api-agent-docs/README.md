# 🌐 REST API Agent

The REST API Agent enables seamless interaction with web services using natural language. It abstracts away the complexity of URLs, HTTP methods, and headers, allowing you to focus on the data you need to fetch, create, or verify.

## 🚀 Key Features

- **Natural Language Mapping**: Translate simple instructions like "Bring me the user with email X" into precise REST API calls.
- **Full CRUD Support**:
    - **Fetch (GET)**: Retrieve resources or collections.
    - **Create (POST)**: Submit new data to the system.
    - **Edit (PUT/PATCH)**: Modify existing records.
    - **Delete (DELETE)**: Remove resources.
- **Intelligent Verification**: Verify API responses against human requirements. The agent can search through nested JSON structures to find and confirm specific values.
- **Context-Aware Analysis**: Provides a summary of the API output in your language (Hebrew or English).
- **Nested Data Handling**: Automatically flattens complex JSON structures to assist smaller LLM models in accurate data extraction.

## 🛠️ How It Works

1. **Intent Translation**: The agent parses your natural language prompt and maps it to a standard REST action (method, endpoint, and payload).
2. **Execution**: The `APITool` performs the actual HTTP request using `httpx`.
3. **Evaluation**: After receiving the response, an LLM analyzes the data against your original prompt.
4. **Outcome**: You receive the raw response, the agent's interpretation, and a verification status (if applicable).

## 🚦 Usage Examples

- *"Fetch all users from the /users endpoint"*
- *"Create a new post with title 'Sanity Test' and content 'Hello World'"*
- *"Edit user 5 and change their city to 'Tel Aviv'"*
- *"Verify that Sarah's email in the users list is 'sarah@test.com'"*
- *"מחק את הפוסט שמספרו 10"*

## ⚙️ Core Logic

- **Semantic Mapping**: The agent follows standard REST conventions (e.g., using plural names for collections).
- **Safety**: Built-in rules prevent the agent from "guessing" IDs or sub-paths; it prefers fetching collections and filtering when IDs are unknown.
- **Robust Parsing**: Advanced JSON extraction ensures that even if the LLM output includes extra text, the core instruction is captured and executed.
