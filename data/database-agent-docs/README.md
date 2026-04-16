# 🗄️ Database Agent

The Database Agent provides a natural language interface to SQLite databases. It allows users to query, analyze, and verify data without writing a single line of SQL.

## 🚀 Key Features

- **Text-to-SQL**: Automatically translates natural language questions (English or Hebrew) into valid SQL SELECT queries.
- **Sample Databases**: Includes built-in support for standard datasets like **Chinook** (Music Store), **Northwind** (Trading), and a **QA Test** database.
- **AI Verification**: Not just a query tool—the agent analyzes the results against your original request to confirm if specific criteria were met.
- **Dynamic Schema Discovery**: Automatically reads the database structure to understand table relationships and columns.
- **Result Analysis**: Provides a human-readable summary of the data returned by the query.

## 🛠️ How It Works

1. **Schema Extraction**: The agent identifies the tables and columns in the selected database.
2. **SQL Generation**: An LLM generates a secure `SELECT` query based on your prompt and the database schema.
3. **Execution**: The query is executed against the SQLite database in a safe, read-only manner (SELECT only).
4. **Analysis & Verification**: The LLM reviews the raw data results and provides a final answer, setting an `is_verified` flag if a specific verification was requested.

## 🚦 Usage Examples

- *"Show me the top 5 customers by revenue"*
- *"Show all products in the Beverages category"*
- *"Verify that there are at least 10 active orders in the Northwind database"*
- *"Check if the user with ID 5 exists in the system"*

## 🛡️ Safety & Security

- **SELECT Only**: To protect data integrity, the Database Agent is restricted to `SELECT` operations. Commands like `INSERT`, `UPDATE`, `DELETE`, or `DROP` are blocked.
- **Isolated Execution**: Database operations are performed using a dedicated connection with row-mapping for secure data handling.
- **Template Reset**: Sample databases can be reset to their original state at any time via the "Reset Database" feature.

## ⚙️ Configuration

- **Custom Path**: You can point the agent to any local `.db` or `.sqlite` file on your system.
- **Sample Selection**: Choose from pre-configured databases to quickly test queries and verification flows.
