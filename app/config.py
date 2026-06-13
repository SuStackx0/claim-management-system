from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = "mock"
    gemini_api_key: str = ""
    db_path: str = str(ROOT / "claims.db")
    policy_path: str = str(ROOT / "data" / "policy_terms.json")
    test_cases_path: str = str(ROOT / "data" / "test_cases.json")
    pipeline_version: str = "1.0.0"


settings = Settings()
