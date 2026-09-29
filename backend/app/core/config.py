import os
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "REVY Breakfast Management System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/breakfast_db"
    
    # SQLite fallback for test / local environment without PostgreSQL daemon running
    FALLBACK_SQLITE_URL: str = "sqlite:///./breakfast.db"

    # JWT / Auth
    JWT_SECRET: str = "breakfast_platform_super_secret_jwt_key_2026_xyz"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://break-fast-management.vercel.app",
        "https://breakfast-management.onrender.com",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        return []

    # Application Defaults
    TIMEZONE: str = "Asia/Kolkata"
    CUTOFF_TIME: str = "12:00"
    DEFAULT_FUND_LIMIT: float = 2500.0

    # Azure Cloud Ready Configurations
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_CONTAINER: str = "breakfast-files"
    ENTRA_CLIENT_ID: str = ""
    ENTRA_TENANT_ID: str = ""
    ENTRA_CLIENT_SECRET: str = ""

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
