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
    groq_api_key: str = ""
    groq_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    db_path: str = str(ROOT / "claims.db")
    policy_path: str = str(ROOT / "data" / "policy_terms.json")
    test_cases_path: str = str(ROOT / "data" / "test_cases.json")
    pipeline_version: str = "1.0.0"
    log_level: str = "INFO"
    # Comma-separated browser origins allowed to call the API, or "*" for any.
    # Same-origin setups (the nginx-proxied docker image) don't need this; it
    # matters when the UI is served from a different origin (e.g. Render static).
    cors_allow_origins: str = "*"


settings = Settings()
