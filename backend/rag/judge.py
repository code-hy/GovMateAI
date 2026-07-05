import re

from openai import OpenAI

from backend.core.config import settings
from backend.rag.metrics import update_relevance_score


def run_builtin_judge(call_id: str, question: str, answer: str):
    try:
        client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.llm_base_url)
        prompt = (
            f"Rate the relevance of the answer to the question on a scale of 0.0 to 1.0.\n"
            f"Question: {question}\nAnswer: {answer}\nReturn ONLY a float number."
        )
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=10,
        )
        score_text = resp.choices[0].message.content.strip()
        score = float(re.findall(r"0\.\d+|1\.0", score_text)[0])
        update_relevance_score(call_id, score)
    except Exception as e:
        print(f"Judge failed for {call_id}: {e}")
