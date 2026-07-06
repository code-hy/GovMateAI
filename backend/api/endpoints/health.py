import traceback

from fastapi import APIRouter, Depends

from backend.api.deps import get_orchestrator
from backend.core.config import settings
from backend.rag.orchestrator import RAGOrchestrator

router = APIRouter()


@router.get("/api/v1/health")
async def health(orchestrator: RAGOrchestrator = Depends(get_orchestrator)):
    try:
        orchestrator.retriever.client.get_collections()
        has_collection = orchestrator.retriever.client.collection_exists(
            settings.qdrant_collection_name
        )
        return {
            "status": "ok",
            "qdrant_connected": True,
            "collection_exists": has_collection,
        }
    except Exception as e:
        return {"status": "error", "qdrant_connected": False, "error": str(e)}


@router.get("/api/v1/debug")
async def debug(orchestrator: RAGOrchestrator = Depends(get_orchestrator)):
    results = {}

    results["llm_base_url"] = settings.llm_base_url
    results["llm_model"] = settings.llm_model
    results["has_api_key"] = bool(settings.deepseek_api_key)

    try:
        orchestrator.retriever.client.get_collections()
        results["qdrant"] = "ok"
        results["collection_exists"] = orchestrator.retriever.client.collection_exists(
            settings.qdrant_collection_name
        )
    except Exception as e:
        results["qdrant"] = f"error: {e}"

    try:
        next(orchestrator.retriever.dense_embedder.embed(["test"]))
        results["dense_embedder"] = "ok"
    except Exception as e:
        results["dense_embedder"] = f"error: {e}"

    try:
        next(orchestrator.retriever.sparse_embedder.embed(["test"]))
        results["sparse_embedder"] = "ok"
    except Exception as e:
        results["sparse_embedder"] = f"error: {e}"

    try:
        response = orchestrator.llm.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": "say hello in one word"}],
            temperature=0.0,
            max_tokens=10,
        )
        results["llm"] = f"ok: {response.choices[0].message.content}"
    except Exception as e:
        results["llm"] = f"error: {traceback.format_exc()}"

    return results
