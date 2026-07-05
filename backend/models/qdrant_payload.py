from pydantic import BaseModel


class QdrantPayload(BaseModel):
    chunk_id: str
    document_url: str
    agency: str
    category: str
    document_title: str
    text: str
