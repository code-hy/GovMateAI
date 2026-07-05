import psycopg2
from backend.core.config import settings


def get_db_connection():
    return psycopg2.connect(settings.database_url)


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
        conn.commit()
        cursor.close()
        conn.close()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Database initialization skipped (non-fatal): {e}")
