"""Application configuration loaded from environment / .env.

All settings are environment-driven (12-factor). Secrets never live in code.
MongoDB Atlas is the single datastore for both application data and the RAG
corpus (chunk text + embedding vectors) via Atlas Vector Search.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- MongoDB (Atlas) ---
    mongo_uri: str = "mongodb://127.0.0.1:27017"
    mongo_db_name: str = "healthcare_rag"

    # --- Auth / JWT ---
    jwt_secret: str = "change_me_to_a_long_random_secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # --- CORS ---
    cors_origins: str = "http://localhost:4200"

    # --- Uploads ---
    upload_dir: str = "data/uploads"
    max_upload_mb: int = 20

    # --- LLM / Embedding provider (configurable per HLD) ---
    llm_provider: str = "openai"          # openai | anthropic | bedrock | ollama
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str = ""                 # set via env; never commit
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # --- Retrieval / Atlas Vector Search ---
    vector_index_name: str = "vector_index"
    vector_search_candidates: int = 100   # numCandidates for ANN search
    retrieval_top_k: int = 5

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
