from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from app.config import settings

_embeddings = None

def get_embeddings() -> OpenAIEmbeddings:
    print('***************************')
    print('***************************')
    print(settings.openai_api_key)
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.openai_api_key,
        )
    return _embeddings


def get_vectorstore(kb_id: str) -> Chroma:
    """Returns a persistent Chroma collection namespaced by kb_id."""
    return Chroma(
        collection_name=kb_id,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_path,
    )