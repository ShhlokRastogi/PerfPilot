import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.env"))

class Settings(BaseSettings):
    PROJECT_NAME: str = "PerfPilot"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./perfpilot.db"

    # LLM Settings (LiteLLM)
    LITELLM_MODEL: str = "groq/llama-3.1-8b-instant"
    LITELLM_FALLBACK_MODEL: str = "groq/llama-3.3-70b-versatile"
    MOCK_LLM: bool = False
    LLM_TIMEOUT_SECONDS: int = 45
    LLM_MAX_RETRIES: int = 2

    # API Keys (read from environment only)
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None

    # Sandbox and Workload Constraints
    ARTIFACTS_DIR: str = "./artifacts"
    MAX_BENCHMARK_DURATION_SEC: int = 60
    SANDBOX_TIMEOUT_SEC: int = 120
    MAX_VUS: int = 100
    
    # Authorized demo and targets (* allows all hosts and auto-sandbox targets)
    ALLOWED_HOSTS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=[ROOT_ENV_PATH, ".env"],
        env_file_encoding="utf-8",
        extra="allow"
    )

settings = Settings()
