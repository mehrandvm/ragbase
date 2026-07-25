from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str
    chroma_path: str = "./chroma_store"
    upload_dir: str  = "./uploads"
    chunk_size: int  = 1000
    chunk_overlap: int = 200
    top_k: int = 5

    class Config:
        env_file = ".env"

settings = Settings()