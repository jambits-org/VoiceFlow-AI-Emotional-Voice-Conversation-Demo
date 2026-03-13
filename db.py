import sqlite3
import uuid
import json
import os
from contextlib import contextmanager
from config import MAX_ATTEMPTS

DB_PATH = os.getenv("DB_PATH", "voiceflow.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS otp_codes (
                code TEXT PRIMARY KEY,
                used INTEGER DEFAULT 0,
                used_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                otp_code TEXT NOT NULL,
                attempts_left INTEGER NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (otp_code) REFERENCES otp_codes(code)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)


def seed_otp(code: str):
    """Insert an OTP code if it doesn't exist yet."""
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO otp_codes (code, used) VALUES (?, 0)",
            (code,)
        )


def verify_and_claim_otp(code: str) -> str | None:
    """Verify OTP, mark as used, create session. Returns session_id or None."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT code, used FROM otp_codes WHERE code = ?", (code,)
        ).fetchone()

        if not row:
            return None
        if row["used"]:
            return None

        # Mark OTP as used
        conn.execute(
            "UPDATE otp_codes SET used = 1, used_at = datetime('now') WHERE code = ?",
            (code,)
        )

        # Create session
        session_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO sessions (id, otp_code, attempts_left) VALUES (?, ?, ?)",
            (session_id, code, MAX_ATTEMPTS)
        )
        return session_id


def get_session(session_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, attempts_left FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not row:
            return None
        return {"id": row["id"], "attempts_left": row["attempts_left"]}


def decrement_attempts(session_id: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE sessions SET attempts_left = attempts_left - 1 WHERE id = ?",
            (session_id,)
        )


def refund_attempt(session_id: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE sessions SET attempts_left = attempts_left + 1 WHERE id = ?",
            (session_id,)
        )


def add_message(session_id: str, role: str, content: str):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content)
        )


def get_history(session_id: str, limit: int = 6) -> list[dict]:
    """Get recent messages for context window."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit)
        ).fetchall()
        # Reverse so oldest first
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
