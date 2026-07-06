import json

from backend.core.config import settings
from backend.core.database import get_db_connection


def save_llm_call(
    call_id: str,
    session_id: str,
    question: str,
    answer: str,
    context_docs: list,
    latency: float,
    prompt_tokens: int,
    completion_tokens: int,
):
    cost = (prompt_tokens / 1000.0 * settings.prompt_cost_per_1k) + (
        completion_tokens / 1000.0 * settings.completion_cost_per_1k
    )
    context_json = json.dumps(
        [
            {"title": d.get("document_title"), "agency": d.get("agency")}
            for d in context_docs
        ]
    )

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO llm_calls
                        (call_id, session_id, question, answer, context,
                         latency_seconds, prompt_tokens, completion_tokens, total_cost)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        call_id,
                        session_id,
                        question,
                        answer,
                        context_json,
                        latency,
                        prompt_tokens,
                        completion_tokens,
                        cost,
                    ),
                )
                conn.commit()
    except Exception as e:
        print(f"Failed to save metrics: {e}")


def update_feedback(call_id: str, feedback: int):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE llm_calls SET feedback = %s WHERE call_id = %s",
                (feedback, call_id),
            )
            conn.commit()


def update_relevance_score(call_id: str, score: float):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE llm_calls SET relevance_score = %s WHERE call_id = %s",
                (score, call_id),
            )
            conn.commit()
