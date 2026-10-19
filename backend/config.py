from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    OLLAMA_BASE_URL: str
    LLM_MODEL: str
    EMBEDDING_MODEL: str= "/opt/aiops/data/models/bge-m3"
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    PROMETHEUS_URL: str
    LOKI_URL: str
    CHUNK_SIZE: int = 500      # SOP 文档切片大小
    CHUNK_OVERLAP: int = 50    # 切片重叠字符数

    class Config:
        env_file = ".env"

settings = Settings()
