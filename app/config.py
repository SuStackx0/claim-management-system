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

    # ── Resilience controls ──────────────────────────────────────────────────
    # Circuit breaker around the live LLM provider. After `fail_max` consecutive
    # infrastructure failures (timeout/429/5xx) the breaker opens and every LLM
    # call fails fast for `cooldown_s` instead of grinding through its full
    # retry+backoff budget — which is what otherwise pins request handlers open
    # and turns one slow dependency into a full API outage. Set fail_max=0 to
    # disable. Has no effect on the deterministic mock provider.
    llm_circuit_fail_max: int = 5
    llm_circuit_cooldown_s: float = 30.0
    # Hard wall-clock ceiling for any single pipeline agent. A backstop against a
    # pathological hang (e.g. a provider that accepts the connection but never
    # responds): on expiry the step fails and the pipeline degrades/stops
    # gracefully rather than holding the HTTP request open indefinitely. Set to 0
    # to disable. Generous by default so legitimate slow retries still complete.
    agent_timeout_s: float = 90.0
    # SQLite busy timeout: how long a writer waits for a competing lock before
    # erroring, instead of failing instantly with "database is locked".
    sqlite_busy_timeout_s: float = 30.0
    # Comma-separated browser origins allowed to call the API, or "*" for any.
    # Same-origin setups (the nginx-proxied docker image) don't need this; it
    # matters when the UI is served from a different origin (e.g. Render static).
    cors_allow_origins: str = "*"


settings = Settings()
