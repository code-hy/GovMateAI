from sentence_transformers import CrossEncoder


class Reranker:
    def __init__(self, model: CrossEncoder):
        self.model = model

    def rerank(
        self, query: str, documents: list[dict], top_k: int = 5
    ) -> list[dict]:
        if not documents:
            return []
        pairs = [[query, doc["text"]] for doc in documents]
        scores = self.model.predict(pairs)
        scored = list(zip(documents, scores))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in scored[:top_k]]
