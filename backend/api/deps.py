from fastapi import Request

from backend.rag.orchestrator import RAGOrchestrator


def get_orchestrator(request: Request) -> RAGOrchestrator:
    return request.app.state.rag_orchestrator
