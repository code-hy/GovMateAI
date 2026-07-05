from fastembed import TextEmbedding

from backend.core.config import settings

_model = TextEmbedding(model_name=settings.embedding_model_name)


def get_embeddings(texts: list[str]) -> tuple[list[list[float]], list[dict]]:
    dense_vectors = []
    sparse_vectors = []
    for dense, sparse in _model.embed(texts):
        dense_vectors.append(dense.tolist())
        sparse_vectors.append(
            {
                "indices": sparse.indices.tolist(),
                "values": sparse.values.tolist(),
            }
        )
    return dense_vectors, sparse_vectors
