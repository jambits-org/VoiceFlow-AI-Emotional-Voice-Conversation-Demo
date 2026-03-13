import sqlite3
import os
from typing import Optional, List, Dict
from contextlib import contextmanager

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
                attempts_left INTEGER NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                otp_code TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (otp_code) REFERENCES otp_codes(code)
            )
        """)


def seed_otp(code: str, max_attempts: int):
    with get_db() as conn:
        existing = conn.execute(
            "SELECT code FROM otp_codes WHERE code = ?", (code,)
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO otp_codes (code, attempts_left) VALUES (?, ?)",
                (code, max_attempts)
            )


def verify_otp(code: str) -> Optional[Dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT code, attempts_left FROM otp_codes WHERE code = ?", (code,)
        ).fetchone()
        if not row:
            return None
        return {"code": row["code"], "attempts_left": row["attempts_left"]}


def get_status(code: str) -> Optional[Dict]:
    return verify_otp(code)


def decrement_attempts(code: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE otp_codes SET attempts_left = attempts_left - 1 WHERE code = ?",
            (code,)
        )


def refund_attempt(code: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE otp_codes SET attempts_left = attempts_left + 1 WHERE code = ?",
            (code,)
        )


def add_message(code: str, role: str, content: str):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO messages (otp_code, role, content) VALUES (?, ?, ?)",
            (code, role, content)
        )


def get_history(code: str, limit: int = 6) -> List[Dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE otp_code = ? ORDER BY id DESC LIMIT ?",
            (code, limit)
        ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
