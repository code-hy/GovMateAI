from pydantic import BaseModel, Field
from typing import List, Optional


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)
    session_id: Optional[str] = None


class CitationSource(BaseModel):
    index: int
    title: str
    agency: str
    url: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[CitationSource] = []


class SuggestionQuestion(BaseModel):
    text: str
    category: str
