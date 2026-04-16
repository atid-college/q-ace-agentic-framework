import sqlite3
import os
import hashlib

DB_PATH = "data/q-ace.db"

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)

    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL, -- 'admin' or 'user'
        group_id INTEGER,
        last_login DATETIME,
        FOREIGN KEY (group_id) REFERENCES groups(id)
    )
    """)

    # Groups Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT
    )
    """)

    # Permissions Table (Group-Tool Mapping)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id INTEGER NOT NULL,
        tool_id TEXT NOT NULL,
        UNIQUE(group_id, tool_id),
        FOREIGN KEY (group_id) REFERENCES groups(id)
    )
    """)

    # Migration: deduplicate permissions that accumulated from previous runs
    # (old schema had no UNIQUE constraint, so every startup added duplicates)
    cursor.execute("""
        DELETE FROM permissions
        WHERE rowid NOT IN (
            SELECT MIN(rowid)
            FROM permissions
            GROUP BY group_id, tool_id
        )
    """)
    dupes_removed = cursor.rowcount
    if dupes_removed > 0:
        print(f"[INIT DB] Removed {dupes_removed} duplicate permission rows from previous runs.")

    # Usage Analytics Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        tool_id TEXT,
        action TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # Seed initial data
    # Admin Role & Group
    cursor.execute("INSERT OR IGNORE INTO groups (name, description) VALUES ('QA Core', 'Full system access')")
    cursor.execute("SELECT id FROM groups WHERE name = 'QA Core'")
    core_group_id = cursor.fetchone()[0]

    # QA BI Group (Limited)
    cursor.execute("INSERT OR IGNORE INTO groups (name, description) VALUES ('QA BI', 'Limited to SQL analysis')")
    cursor.execute("SELECT id FROM groups WHERE name = 'QA BI'")
    bi_group_id = cursor.fetchone()[0]

    # Default Tools for QA Core (All)
    all_tools = ["sqlite", "api", "spec_analyzer", "jenkins", "github_actions", "selenium", "playwright", "cypress", "postman", "github", "jira", "qase"]
    for tool in all_tools:
        cursor.execute("INSERT OR IGNORE INTO permissions (group_id, tool_id) VALUES (?, ?)", (core_group_id, tool))

    # Default Tools for QA BI (SQL only)
    cursor.execute("INSERT OR IGNORE INTO permissions (group_id, tool_id) VALUES (?, ?)", (bi_group_id, "sqlite"))

    # Chat Sessions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # Chat Messages Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        role TEXT NOT NULL, -- 'user' or 'assistant'
        content TEXT NOT NULL,
        type TEXT DEFAULT 'text', -- 'text' or 'workflow'
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
    )
    """)

    # User Settings Table (Persistent LLM Config)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_settings (
        user_id INTEGER PRIMARY KEY,
        provider TEXT DEFAULT 'gemini',
        gemini_model TEXT DEFAULT 'gemini-2.0-flash',
        ollama_model TEXT DEFAULT 'gemma3:1b',
        api_key TEXT,
        base_url TEXT DEFAULT 'http://localhost:11434',
        json_config TEXT, -- Stores specific configs like openai, anthropic, etc.
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Migration: Add json_config column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE user_settings ADD COLUMN json_config TEXT")
    except sqlite3.OperationalError:
        pass

    # Browser Agent History Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS browser_agent_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        prompt TEXT NOT NULL,
        logs TEXT NOT NULL, -- JSON string of the log array
        history_json TEXT, -- Serialized history list from browser-use
        result TEXT,
        status TEXT DEFAULT 'success',
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Migration: Add status column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE browser_agent_history ADD COLUMN status TEXT DEFAULT 'success'")
    except sqlite3.OperationalError:
        pass

    # Migration: Add history_json column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE browser_agent_history ADD COLUMN history_json TEXT")
    except sqlite3.OperationalError:
        pass

    # Migration: Add ai_analysis column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE browser_agent_history ADD COLUMN ai_analysis TEXT")
    except sqlite3.OperationalError:
        pass

    # Browser Agent Persistent Configuration Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS browser_agent_config (
        user_id INTEGER PRIMARY KEY,
        agent_config TEXT,
        browser_config TEXT,
        llm_config TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Mobile Agent Persistent Configuration Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mobile_agent_config (
        user_id INTEGER PRIMARY KEY,
        appium_config TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Mobile Agent History Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mobile_agent_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        prompt TEXT NOT NULL,
        logs TEXT NOT NULL,
        history_json TEXT,
        result TEXT,
        status TEXT DEFAULT 'success',
        ai_analysis TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Migration: Add status column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE mobile_agent_history ADD COLUMN status TEXT DEFAULT 'success'")
    except sqlite3.OperationalError:
        pass


    # Database Agent History Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS db_agent_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        prompt TEXT NOT NULL,
        result_json TEXT NOT NULL,
        active_db TEXT,
        sample_db TEXT,
        ai_analysis TEXT,
        is_verified BOOLEAN,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # API Agent History Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS api_agent_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        prompt TEXT NOT NULL,
        result_json TEXT NOT NULL,
        server_url TEXT,
        selected_server TEXT,
        llm_intent TEXT,
        ai_analysis TEXT,
        is_verified BOOLEAN,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    admin_password_hash = hashlib.sha256("admin123".encode()).hexdigest()
    cursor.execute("INSERT OR IGNORE INTO users (username, password_hash, role, group_id) VALUES (?, ?, ?, ?)", 
                   ("admin", admin_password_hash, "admin", core_group_id))

    # Seed initial chat sessions for admin
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    admin_id = cursor.fetchone()[0]

    # Seed flows for ALL existing users to ensure visibility
    users_list = cursor.execute("SELECT id, username FROM users").fetchall()
    print(f"Found {len(users_list)} users for seeding.")
    for user_row in users_list:
        u_id, username = user_row
        print(f"Seeding flows for user: {username} (ID: {u_id})")
        
        # Session 1: API to SQL Flow
        cursor.execute("INSERT INTO chat_sessions (user_id, title) VALUES (?, ?)", (u_id, "API to SQL Verification Flow"))
        session1_id = cursor.lastrowid
        
        s1_messages = [
            ('user', 'Fetch all users from the /users endpoint and verify if they exist in the local SQLite database.'),
            ('assistant', 'I will start by fetching the users via the API tool, then I will query the SQLite database to verify their existence.'),
            ('assistant', '{"type": "workflow", "title": "Verification Flow", "status": "Completed", "steps": [{"id": 1, "label": "Fetch API Data", "tool": "api", "status": "completed"}, {"id": 2, "label": "Parse JSON", "tool": "ai", "status": "completed"}, {"id": 3, "label": "Query SQLite", "tool": "sqlite", "status": "completed"}, {"id": 4, "label": "AI Verification", "tool": "ai", "status": "completed"}]}')
        ]
        for role, content in s1_messages:
            msg_type = 'workflow' if content.startswith('{') else 'text'
            cursor.execute("INSERT INTO chat_messages (session_id, role, content, type) VALUES (?, ?, ?, ?)", (session1_id, role, content, msg_type))

        # Session 2: Spec to Jenkins Flow
        cursor.execute("INSERT INTO chat_sessions (user_id, title) VALUES (?, ?)", (u_id, "Spec to Jenkins Automation Flow"))
        session2_id = cursor.lastrowid
        
        s2_messages = [
            ('user', 'Analyze the login-spec.pdf and generate automation scripts for Jenkins.'),
            ('assistant', 'Analyzing the technical specification now. I will extract the requirements and map them to Jenkins pipeline steps.'),
            ('assistant', '{"type": "workflow", "title": "Automation Pipeline", "status": "Completed", "steps": [{"id": 1, "label": "Analyze PDF Spec", "tool": "spec_analyzer", "status": "completed"}, {"id": 2, "label": "Generate Scripts", "tool": "ai", "status": "completed"}, {"id": 3, "label": "Jenkins Integration", "tool": "jenkins", "status": "completed"}]}')
        ]
        for role, content in s2_messages:
            msg_type = 'workflow' if content.startswith('{') else 'text'
            cursor.execute("INSERT INTO chat_messages (session_id, role, content, type) VALUES (?, ?, ?, ?)", (session2_id, role, content, msg_type))

    conn.commit()
    conn.close()
    print("Seeding completed successfully.")
    print(f"Database initialized at {DB_PATH}")

if __name__ == "__main__":
    init_db()
