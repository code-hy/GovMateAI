import json
import os
from pathlib import Path

import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

st.set_page_config(page_title="GovMate AI Monitoring", layout="wide")
st.title("GovMate AI Monitoring Dashboard")

DB_URL = os.environ.get("DATABASE_URL") or "postgresql://postgres:postgres@localhost:5435/govmate_db"
DATA_DIR = Path(__file__).parent.parent / "datasets"
CALLS_FILE = DATA_DIR / "llm_calls.json"


def get_data():
    try:
        conn = psycopg2.connect(DB_URL, connect_timeout=2)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            SELECT call_id, session_id, question, answer, latency_seconds,
                   prompt_tokens, completion_tokens, total_cost, feedback, relevance_score,
                   created_at
            FROM llm_calls
            ORDER BY created_at DESC
            LIMIT 500
        """
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return pd.DataFrame(rows)
    except Exception:
        if CALLS_FILE.exists():
            with open(CALLS_FILE) as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            if not df.empty and "created_at" in df.columns:
                df["created_at"] = pd.to_datetime(df["created_at"])
            return df
        return pd.DataFrame()


df = get_data()

if df.empty:
    st.warning("No data yet. Ask some questions in the main chat app first!")
    st.stop()

if "total_cost" not in df.columns:
    df["total_cost"] = 0.0
if "feedback" not in df.columns:
    df["feedback"] = 0
if "relevance_score" not in df.columns:
    df["relevance_score"] = None
if "latency_seconds" not in df.columns:
    df["latency_seconds"] = 0.0
if "prompt_tokens" not in df.columns:
    df["prompt_tokens"] = 0
if "completion_tokens" not in df.columns:
    df["completion_tokens"] = 0

df["created_at"] = pd.to_datetime(df["created_at"])
df = df.sort_values("created_at")

st.sidebar.header("Filters")
agency_filter = st.sidebar.multiselect(
    "Agency", options=["ATO", "Services Australia", "General"], default=[]
)
date_range = st.sidebar.date_input("Date range", [])

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Queries", len(df))
col2.metric("Avg Latency (s)", f"{df['latency_seconds'].mean():.2f}")
col3.metric("Total Cost ($)", f"{df['total_cost'].sum():.6f}")
col4.metric("Avg Relevance", f"{df['relevance_score'].mean():.2f}" if df["relevance_score"].notna().any() else "N/A")

st.markdown("---")

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("Query Latency over Time")
    st.line_chart(df.set_index("created_at")["latency_seconds"])

with chart_col2:
    st.subheader("Cumulative Cost")
    cost_series = df.set_index("created_at")["total_cost"].cumsum()
    st.area_chart(cost_series)

chart_col3, chart_col4 = st.columns(2)

with chart_col3:
    st.subheader("User Feedback Distribution")
    fb = df["feedback"].value_counts().reindex([-1, 0, 1], fill_value=0)
    fb.index = ["Thumbs Down", "No Feedback", "Thumbs Up"]
    st.bar_chart(fb)

with chart_col4:
    st.subheader("LLM-as-a-Judge Relevance Score")
    judge_df = df[df["relevance_score"].notna() & (df["relevance_score"] > 0)]
    if not judge_df.empty:
        st.line_chart(judge_df.set_index("created_at")["relevance_score"])
    else:
        st.info("Waiting for LLM Judge background tasks to complete...")

st.markdown("---")
st.subheader("Token Usage")
tokens_col1, tokens_col2 = st.columns(2)
with tokens_col1:
    st.bar_chart(df.set_index("created_at")["prompt_tokens"])
with tokens_col2:
    st.bar_chart(df.set_index("created_at")["completion_tokens"])

st.markdown("---")
st.subheader("Recent Conversations")
display_df = df[["question", "answer", "latency_seconds", "total_cost", "feedback", "relevance_score"]].head(10)
display_df.columns = ["Question", "Answer", "Latency (s)", "Cost ($)", "Feedback", "Relevance"]
st.dataframe(display_df, use_container_width=True)
