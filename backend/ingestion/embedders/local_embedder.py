from fastembed import SparseTextEmbedding, TextEmbedding

from backend.core.config import settings

_dense_model = TextEmbedding(model_name=settings.embedding_model_name)
_sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")


def get_embeddings(texts: list[str]) -> tuple[list[list[float]], list[dict]]:
    dense_vectors = [v.tolist() for v in _dense_model.embed(texts)]
    sparse_vectors = [
        {
            "indices": s.indices.tolist(),
            "values": s.values.tolist(),
        }
        for s in _sparse_model.embed(texts)
    ]
    return dense_vectors, sparse_vectors
