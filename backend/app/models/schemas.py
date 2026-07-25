from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class KnowledgeBase(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime = datetime.now()


class IngestResponse(BaseModel):
    kb_id: str
    file_name: str
    chunks_stored: int


class Citation(BaseModel):
    source: str          # filename
    page: Optional[int]  # page number if PDF
    chunk: str           # the actual chunk text shown to user


class QueryRequest(BaseModel):
    question: str
    chat_history: List[dict] = []   # [{"role": "human"|"ai", "content": "..."}]


class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation]