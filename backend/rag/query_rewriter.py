REWRITE_PROMPT = """You are a query reformulation assistant for an Australian Government RAG system.
Your task: rewrite the user's question using formal Australian Government terminology.

Examples:
- "can i claim the dole" → "JobSeeker Payment eligibility"
- "centrelink payments for unemployed" → "Services Australia unemployment benefits"
- "newstart allowance" → "JobSeeker Payment"
- "how do i get money from the government" → "what government payments am I eligible for"

Rules:
1. Replace slang/informal terms with official program names
2. Keep the original question's intent
3. Output ONLY the rewritten query, no explanations
4. If the query is already formal, return it unchanged

Rewrite this query:"""


def rewrite_query(query: str, llm_client) -> str:
    try:
        response = llm_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": REWRITE_PROMPT},
                {"role": "user", "content": query},
            ],
            temperature=0.0,
            max_tokens=100,
        )
        rewritten = response.choices[0].message.content.strip()
        if rewritten:
            return rewritten
    except Exception:
        pass
    return query
