from __future__ import annotations
import contextvars
import logging
import logging.config
import os
import sys

_configured = False

# Correlation id for the in-flight HTTP request. Set by the API middleware and
# read by RequestIdFilter so EVERY log line emitted while serving a request —
# including deep in the pipeline — is stamped with the same id. contextvars
# propagate across await points and asyncio.to_thread, so the id follows the
# request through async agents and the off-loop DB write. Defaults to "-" for
# logs emitted outside any request (startup, background work).
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

# request_id sits right after the level so a line reads:
#   2026-06-14 10:00:00 INFO [req-1a2b3c4d] app.core.orchestrator: [CLM-XYZ] ...
# giving two correlation handles at a glance: req-* (one HTTP request) and the
# in-message CLM-* (one claim). Greppable by either.
_FORMAT = "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"
# Libraries that are chatty at INFO/DEBUG and drown out the claim story.
_NOISY = ("httpx", "httpcore", "google.genai", "google_genai", "urllib3", "uvicorn.access")


class RequestIdFilter(logging.Filter):
    """Stamp every record with the current request id so the formatter's
    %(request_id)s field always resolves, even for records from third-party
    loggers that never heard of our contextvar."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def _under_pytest() -> bool:
    return "PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules


def _build_dict_config(level: str) -> dict:
    """One concise stdout handler on root; noisy third parties pinned to WARNING."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {"request_id": {"()": "app.core.logging_config.RequestIdFilter"}},
        "formatters": {"plum": {"format": _FORMAT, "datefmt": _DATEFMT}},
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "plum",
                "filters": ["request_id"],
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
