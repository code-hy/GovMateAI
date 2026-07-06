from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    deepseek_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 1000

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""
    qdrant_https: bool = False
    qdrant_collection_name: str = "government_documents"
    dense_vector_size: int = 384
    embedding_model_name: str = "BAAI/bge-small-en-v1.5"

    retrieval_top_k: int = 15
    rerank_top_k: int = 5
    max_context_characters: int = 3000

    max_history_turns: int = 2

    database_url: str = "postgresql://postgres:postgres@localhost:5432/govmate_db"

    prompt_cost_per_1k: float = 0.00014
    completion_cost_per_1k: float = 0.00028


settings = Settings()
