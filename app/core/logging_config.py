from __future__ import annotations
import logging
import logging.config
import os
import sys

_configured = False

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"
# Libraries that are chatty at INFO/DEBUG and drown out the claim story.
_NOISY = ("httpx", "httpcore", "google.genai", "google_genai", "urllib3", "uvicorn.access")


def _under_pytest() -> bool:
    return "PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules


def _build_dict_config(level: str) -> dict:
    """One concise stdout handler on root; noisy third parties pinned to WARNING."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"plum": {"format": _FORMAT, "datefmt": _DATEFMT}},
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "plum",
            }
        },
        "root": {"level": level, "handlers": ["console"]},
        "loggers": {name: {"level": "WARNING"} for name in _NOISY},
    }


def configure_logging() -> None:
    """Configure process-wide logging once. Idempotent and safe to call repeatedly.

    Installs a single stdout handler with a concise format and quiets noisy
    third-party loggers. Under pytest we do NOT install handlers or touch the
    root logger — the test runner owns logging, and reconfiguring it mid-run
    deadlocks the ASGI event loop. We still quiet the noisy libraries there.
    """
    global _configured
    if _configured:
        return
    _configured = True

    # Always safe: keep third-party loggers from flooding the output.
    for name in _NOISY:
        logging.getLogger(name).setLevel(logging.WARNING)

    if _under_pytest():
        return

    level = os.getenv("LOG_LEVEL", "INFO").upper()
    if not hasattr(logging, level):
        level = "INFO"
    logging.config.dictConfig(_build_dict_config(level))


def reset_configured() -> None:
    """Reset the one-time guard. Used by tests."""
    global _configured
    _configured = False
