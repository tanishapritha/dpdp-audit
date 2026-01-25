from typing import List, Union
from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Company Compliance Engine"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "DEFAULT_SECRET_KEY"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    SQLALCHEMY_DATABASE_URL: str = "postgresql://user:pass@localhost:5432/dbname"
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    USE_AGENT_BASED_EVALUATION: bool = True  # Toggle between legacy and agent-based system

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
