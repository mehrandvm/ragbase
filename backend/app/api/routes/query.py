import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core.graph import stream_query
from app.core.registry import get_kb
from app.models.schemas import QueryRequest

router = APIRouter(prefix="/kb", tags=["query"])


async def sse_generator(
    kb_id: str, question: str, chat_history: list
) -> AsyncGenerator[str, None]:
    async for chunk in stream_query(kb_id, question, chat_history):
        if isinstance(chunk, dict):
            # citations payload — sent as a labelled SSE event so frontend can parse it
            yield f"data: [CITATIONS]{json.dumps(chunk)}\n\n"
        else:
            # escape newlines so SSE framing stays intact
            safe = chunk.replace("\n", "\\n")
            yield f"data: {safe}\n\n"

    yield "data: [DONE]\n\n"


@router.post("/{kb_id}/query")
async def query(kb_id: str, body: QueryRequest):
    if not get_kb(kb_id):
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    return StreamingResponse(
        sse_generator(kb_id, body.question, body.chat_history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disables nginx buffering if behind a proxy
        },
    )
