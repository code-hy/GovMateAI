from fastembed import SparseTextEmbedding, TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    Fusion,
    FusionQuery,
    MatchValue,
    Prefetch,
)

from backend.core.config import settings


class Retriever:
    def __init__(self, qdrant_client: QdrantClient):
        self.client = qdrant_client
        self.dense_embedder = TextEmbedding(model_name=settings.embedding_model_name)
        self.sparse_embedder = SparseTextEmbedding(model_name="Qdrant/bm25")

    def retrieve(self, query: str, agency_filter: str | None = None) -> list[dict]:
        query_dense = next(self.dense_embedder.embed([query])).tolist()
        sparse_result = next(self.sparse_embedder.embed([query]))
        query_sparse = {
            "indices": sparse_result.indices.tolist(),
            "values": sparse_result.values.tolist(),
        }

        prefetch_list = [
            Prefetch(query=query_dense, using="dense", limit=settings.retrieval_top_k),
            Prefetch(
                query=query_sparse, using="sparse", limit=settings.retrieval_top_k
            ),
        ]

        qdrant_filter = None
        if agency_filter:
            qdrant_filter = Filter(
                must=[
                    FieldCondition(
                        key="agency", match=MatchValue(value=agency_filter)
                    )
                ]
            )

        results = self.client.query_points(
            collection_name=settings.qdrant_collection_name,
            prefetch=prefetch_list,
            query=FusionQuery(fusion=Fusion.RRF),
            limit=settings.retrieval_top_k,
            query_filter=qdrant_filter,
        ).points

        return [hit.payload for hit in results]
