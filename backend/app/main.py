# backend/app/main.py
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import kb, ingest, query
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ensure required directories exist on startup
    Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="ragbase",
    description="Multi-tenant knowledge base API with corrective RAG and LangGraph",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # SvelteKit dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(kb.router)
app.include_router(ingest.router)
app.include_router(query.router)


# Entry point. Lifespan creates chroma_store/ and uploads/ on first boot so
# neither the vector store nor the file upload handler need to worry about missing dirs.
# CORS is locked to the SvelteKit dev port for now — widen allow_origins to ["*"]
# or your prod domain before deploying.