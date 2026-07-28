from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key:     str
    chroma_path:        str   = "./chroma_store"
    upload_dir:         str   = "./uploads"
    chunk_size:         int   = 1000
    chunk_overlap:      int   = 200
    top_k:              int   = 5

    # HuggingFace
    embedding_provider: str   = "huggingface"          # "huggingface" | "openai"
    hf_embedding_model: str   = "BAAI/bge-small-en-v1.5"
    hf_reranker_model:  str   = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_threshold: float = 0.0

    class Config:
        env_file = ".env"

settings = Settings()