SYSTEM_PROMPT = """You are GovMate AI, a highly accurate assistant for Australian Government services (ATO and Services Australia).
RULES:
1. Answer STRICTLY using the <context> provided. Do not use outside knowledge.
2. Cite sources using the format 【X】 where X is the context number.
3. If the context is missing information, say "I cannot find specific information regarding this in the current documents."
4. Be concise and helpful."""


def build_prompt(
    query: str, context_docs: list[dict], history: list[dict] | None = None
) -> list[dict]:
    context_str = ""
    for i, doc in enumerate(context_docs, 1):
        context_str += (
            f"[{i}] Agency: {doc['agency']} | Title: {doc['document_title']} | "
            f"URL: {doc['document_url']}\n{doc['text']}\n\n"
        )

    user_content = f"<context>\n{context_str}</context>\n\n"

    if history:
        user_content += "<chat_history>\n"
        for turn in history:
            user_content += f"{turn['role']}: {turn['content']}\n"
        user_content += "</chat_history>\n\n"

    user_content += (
        f"<question>\n{query}\n</question>\n"
        "Please answer the question using the context."
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_content})
    return messages
