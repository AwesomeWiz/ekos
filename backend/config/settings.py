import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "AEKOS - Autonomous Enterprise Knowledge Operating System"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    CORS_ORIGINS: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]

    # JWT Settings
    JWT_SECRET: str = "change-this-to-a-secure-secret-key-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # PostgreSQL / Database Settings
    POSTGRES_URL: str = "sqlite:///./aekos.db"

    # Placeholder Settings for future modules
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    CHROMA_PATH: str = "./data/chroma"
    OLLAMA_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "qwen3:1.7b"
    EMBEDDING_MODEL: str = "BAAI/bge-base-en-v1.5"
    GITHUB_TOKEN: str = ""
    GITHUB_OWNER: str = ""
    GITHUB_REPO: str = ""
    JIRA_API_TOKEN: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
