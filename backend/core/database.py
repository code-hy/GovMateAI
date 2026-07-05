import json
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

from backend.core.config import settings


def get_db_connection():
    return psycopg2.connect(settings.database_url, connect_timeout=2)


def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_calls (
                id SERIAL PRIMARY KEY,
                call_id VARCHAR(255) UNIQUE NOT NULL,
                session_id VARCHAR(255),
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                context TEXT,
                latency_seconds FLOAT,
                prompt_tokens INT DEFAULT 0,
                completion_tokens INT DEFAULT 0,
                total_cost FLOAT DEFAULT 0.0,
                feedback INT DEFAULT 0,
                relevance_score FLOAT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id VARCHAR(255) PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Database initialization skipped (non-fatal): {e}")


def create_session(session_id: str, title: str):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO sessions (session_id, title) VALUES (%s, %s) ON CONFLICT (session_id) DO NOTHING",
                    (session_id, title),
                )
                conn.commit()
    except Exception as e:
        print(f"Failed to create session: {e}")


def list_sessions() -> list[dict]:
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT session_id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC LIMIT 50"
                )
                return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"Failed to list sessions: {e}")
        return []


def get_session_messages(session_id: str) -> list[dict]:
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT call_id, question, answer, created_at FROM llm_calls WHERE session_id = %s ORDER BY created_at ASC",
                    (session_id,),
                )
                return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"Failed to get session messages: {e}")
        return []


def update_session_timestamp(session_id: str):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE sessions SET updated_at = %s WHERE session_id = %s",
                    (datetime.now(), session_id),
                )
                conn.commit()
    except Exception as e:
        print(f"Failed to update session timestamp: {e}")
