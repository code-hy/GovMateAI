import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from openai import OpenAI
from qdrant_client import QdrantClient
from sentence_transformers import CrossEncoder

from backend.api.router import api_router
from backend.core.config import settings
from backend.core.database import init_db
from backend.rag.orchestrator import RAGOrchestrator

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    app.state.qdrant_client = QdrantClient(
        host=settings.qdrant_host, port=settings.qdrant_port
    )
    app.state.openai_client = OpenAI(
        api_key=settings.deepseek_api_key, base_url=settings.llm_base_url
    )
    app.state.reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    app.state.rag_orchestrator = RAGOrchestrator(
        qdrant_client=app.state.qdrant_client,
        openai_client=app.state.openai_client,
        reranker=app.state.reranker,
        config=settings,
    )

    yield

    del app.state.reranker
    app.state.openai_client.close()
    app.state.qdrant_client.close()


app = FastAPI(title="GovMate AI", version="1.0.0", lifespan=lifespan)

app.mount(
    "/static",
    StaticFiles(directory=os.path.join(BASE_DIR, "frontend", "static")),
    name="static",
)
templates = Jinja2Templates(
    directory=os.path.join(BASE_DIR, "frontend", "templates")
)


@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse(request, "index.html")


app.include_router(api_router)
