from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，优先从环境变量读取"""
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ainews"
    redis_url: str = "redis://localhost:6379/0"
    deepseek_api_key: str = ""
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
