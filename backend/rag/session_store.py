import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SESSIONS_FILE = os.path.join(BASE_DIR, "datasets", "sessions.json")
CALLS_FILE = os.path.join(BASE_DIR, "datasets", "llm_calls.json")


def _ensure_file(path):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump([], f)


def _read(path):
    _ensure_file(path)
    with open(path, "r") as f:
        return json.load(f)


def _write(path, data):
    _ensure_file(path)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def create_session(session_id: str, title: str):
    sessions = _read(SESSIONS_FILE)
    existing = [s for s in sessions if s["session_id"] == session_id]
    now = datetime.now().isoformat()
    if existing:
        existing[0]["updated_at"] = now
    else:
        sessions.append({
            "session_id": session_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
        })
    _write(SESSIONS_FILE, sessions)


def list_sessions() -> list[dict]:
    sessions = _read(SESSIONS_FILE)
    sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
    return sessions[:50]


def get_session_messages(session_id: str) -> list[dict]:
    calls = _read(CALLS_FILE)
    return [c for c in calls if c.get("session_id") == session_id]


def save_llm_call_local(
    call_id: str,
    session_id: str,
    question: str,
    answer: str,
    context_docs: list,
    latency: float,
    prompt_tokens: int,
    completion_tokens: int,
):
    calls = _read(CALLS_FILE)
    calls.append({
        "call_id": call_id,
        "session_id": session_id,
        "question": question,
        "answer": answer,
        "context": [
            {"title": d.get("document_title"), "agency": d.get("agency")}
            for d in context_docs
        ],
        "latency_seconds": latency,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "feedback": 0,
        "relevance_score": None,
        "created_at": datetime.now().isoformat(),
    })
    _write(CALLS_FILE, calls)


def update_feedback_local(call_id: str, feedback: int):
    calls = _read(CALLS_FILE)
    for c in calls:
        if c["call_id"] == call_id:
            c["feedback"] = feedback
            break
    _write(CALLS_FILE, calls)


def update_relevance_local(call_id: str, score: float):
    calls = _read(CALLS_FILE)
    for c in calls:
        if c["call_id"] == call_id:
            c["relevance_score"] = score
            break
    _write(CALLS_FILE, calls)
