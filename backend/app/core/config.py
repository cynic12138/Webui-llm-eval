from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "LLM Eval Platform"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Deployment
    HOST_IP: str = "localhost"
    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 3000

    # Database — atomic fields (new names)
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "llmeval"
    DB_PASS: str = "llmeval123"
    DB_NAME: str = "llmeval"

    # Database — legacy names (backward compat)
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    # Assembled URLs (auto-generated, can be overridden)
    DATABASE_URL: str = ""
    DATABASE_URL_SYNC: str = ""

    # Redis — atomic fields
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Assembled Redis URLs (auto-generated, can be overridden)
    REDIS_URL: str = ""
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    # MinIO (new names)
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_BUCKET: str = "llmeval"
    MINIO_SECURE: bool = False

    # MinIO — legacy names (backward compat)
    MINIO_ROOT_USER: str = ""
    MINIO_ROOT_PASSWORD: str = ""

    # Security
    SECRET_KEY: str = "supersecretkey-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Agent (AI Assistant) — fallback defaults; overridden by DB AgentModelConfig per user
    AGENT_MODEL_PROVIDER: str = "openai"
    AGENT_MODEL_NAME: str = ""
    AGENT_API_KEY: str = ""
    AGENT_BASE_URL: Optional[str] = None
    AGENT_MAX_TOKENS: int = 4096
    AGENT_TEMPERATURE: float = 0.7
    AGENT_MAX_TOOL_CALLS_PER_TURN: int = 5

    # CORS
    CORS_EXTRA_ORIGINS: str = ""
    BACKEND_CORS_ORIGINS: list[str] = []

    @model_validator(mode="after")
    def assemble_urls(self) -> "Settings":
        # Legacy variable mapping: old names → new names
        if self.POSTGRES_USER and self.DB_USER == "llmeval":
            self.DB_USER = self.POSTGRES_USER
        if self.POSTGRES_PASSWORD and self.DB_PASS == "llmeval123":
            self.DB_PASS = self.POSTGRES_PASSWORD
        if self.POSTGRES_DB and self.DB_NAME == "llmeval":
            self.DB_NAME = self.POSTGRES_DB
        if self.MINIO_ROOT_USER and self.MINIO_ACCESS_KEY == "minioadmin":
            self.MINIO_ACCESS_KEY = self.MINIO_ROOT_USER
        if self.MINIO_ROOT_PASSWORD and self.MINIO_SECRET_KEY == "minioadmin123":
            self.MINIO_SECRET_KEY = self.MINIO_ROOT_PASSWORD

        # Database URLs
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            )
        if not self.DATABASE_URL_SYNC:
            self.DATABASE_URL_SYNC = (
                f"postgresql://{self.DB_USER}:{self.DB_PASS}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            )

        # Redis URLs
        if not self.REDIS_URL:
            self.REDIS_URL = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/1"
        if not self.CELERY_RESULT_BACKEND:
            self.CELERY_RESULT_BACKEND = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/2"

        # CORS origins
        if not self.BACKEND_CORS_ORIGINS:
            origins = [
                f"http://localhost:{self.FRONTEND_PORT}",
                f"http://127.0.0.1:{self.FRONTEND_PORT}",
            ]
            if self.HOST_IP not in ("localhost", "127.0.0.1"):
                origins.append(f"http://{self.HOST_IP}:{self.FRONTEND_PORT}")
            if self.CORS_EXTRA_ORIGINS:
                for origin in self.CORS_EXTRA_ORIGINS.split(","):
                    origin = origin.strip()
                    if origin:
                        origins.append(origin)
            self.BACKEND_CORS_ORIGINS = origins

        return self

    class Config:
        env_file = ["../.env", ".env"]
        case_sensitive = True


settings = Settings()
