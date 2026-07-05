import re


def format_citations(answer: str, source_docs: list[dict]) -> list[dict]:
    matches = re.findall(r"【(\d+)】", answer)
    unique_indices = {int(m) for m in matches}
    sources = []
    for idx in sorted(unique_indices):
        if 0 < idx <= len(source_docs):
            doc = source_docs[idx - 1]
            sources.append(
                {
                    "index": idx,
                    "title": doc.get("document_title", "Unknown"),
                    "agency": doc.get("agency", "Unknown"),
                    "url": doc.get("document_url", "#"),
                }
            )
    return sources
