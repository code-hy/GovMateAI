from fastapi import APIRouter, Depends

from backend.api.deps import get_orchestrator
from backend.rag.orchestrator import RAGOrchestrator

router = APIRouter()


@router.get("/api/v1/health")
async def health(orchestrator: RAGOrchestrator = Depends(get_orchestrator)):
    try:
        orchestrator.retriever.client.get_collections()
        return {"status": "ok", "qdrant_connected": True}
    except Exception:
        return {"status": "error", "qdrant_connected": False}
