import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "mock")  # "gemini" | "mock"
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    db_path: str = os.getenv("DB_PATH", str(ROOT / "claims.db"))
    policy_path: str = os.getenv("POLICY_PATH", str(ROOT / "data" / "policy_terms.json"))
    test_cases_path: str = os.getenv("TEST_CASES_PATH", str(ROOT / "data" / "test_cases.json"))
    pipeline_version: str = "1.0.0"

settings = Settings()
