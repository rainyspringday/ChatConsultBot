import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "auth.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(chat_id) REFERENCES chat_sessions(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS company_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                company_name TEXT NOT NULL,
                current_state_json TEXT NOT NULL,
                todo_plan_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_tokens (
                token TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_message_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                rating INTEGER NOT NULL CHECK (rating IN (-1, 1)),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(message_id, username),
                FOREIGN KEY(message_id) REFERENCES chat_messages(id)
            )
            """
        )
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(company_analyses)").fetchall()
        }
        if "benchmark_company" not in columns:
            conn.execute(
                "ALTER TABLE company_analyses ADD COLUMN benchmark_company TEXT"
            )
        if "maturity_score" not in columns:
            conn.execute(
                "ALTER TABLE company_analyses ADD COLUMN maturity_score INTEGER"
            )
        if "focus_topics_json" not in columns:
            conn.execute(
                "ALTER TABLE company_analyses ADD COLUMN focus_topics_json TEXT"
            )
        if "revenue_series_json" not in columns:
            conn.execute(
                "ALTER TABLE company_analyses ADD COLUMN revenue_series_json TEXT"
            )
        if "user_rating" not in columns:
            conn.execute(
                "ALTER TABLE company_analyses ADD COLUMN user_rating INTEGER"
            )
        conn.commit()
