from fastapi import APIRouter

from backend.api.endpoints import chat, health, suggestions

api_router = APIRouter()
api_router.include_router(chat.router)
api_router.include_router(suggestions.router)
api_router.include_router(health.router)
