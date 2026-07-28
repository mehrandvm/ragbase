# backend/app/core/vectorstore.py
from langchain_chroma import Chroma
from app.config import settings


def get_embeddings():
    if settings.embedding_provider == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(
            model_name=settings.hf_embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},  # improves cosine similarity
        )
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=settings.openai_api_key,
    )


def get_vectorstore(kb_id: str) -> Chroma:
    """Returns a persistent Chroma collection namespaced by kb_id."""
    return Chroma(
        collection_name=kb_id,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_path,
    )


# get_embeddings() is provider-aware — reads EMBEDDING_PROVIDER from config.
# "huggingface" uses a local sentence-transformers model (no API cost, runs on CPU).
# "openai" uses text-embedding-3-small via API.
# normalize_embeddings=True on HuggingFace ensures vectors are unit-length,
# which is required for cosine similarity to work correctly in Chroma.
# Important: don't mix providers across ingest and query for the same KB —
# embeddings must come from the same model that indexed the chunks.