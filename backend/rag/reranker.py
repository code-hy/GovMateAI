class Reranker:
    def __init__(self, model=None):
        self.model = model

    def rerank(
        self, query: str, documents: list[dict], top_k: int = 5
    ) -> list[dict]:
        if not documents:
            return []
        if self.model is None:
            return documents[:top_k]
        pairs = [[query, doc["text"]] for doc in documents]
        scores = self.model.predict(pairs)
        scored = list(zip(documents, scores))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in scored[:top_k]]
