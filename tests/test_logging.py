from __future__ import annotations
import asyncio
import logging
import re

from app.core.logging_config import (
    _build_dict_config,
    configure_logging,
    reset_configured,
)
from app.core.orchestrator import Orchestrator
from app.llm.mock_client import MockClient
from app.models.domain import ClaimSubmission


def test_dict_config_has_one_console_handler_and_level():
    cfg = _build_dict_config("DEBUG")
    assert cfg["root"]["level"] == "DEBUG"
    assert cfg["root"]["handlers"] == ["console"]
    assert cfg["handlers"]["console"]["class"] == "logging.StreamHandler"
    # dictConfig replaces handlers wholesale, so it is inherently idempotent —
    # building twice yields one console handler each time, never a duplicate set.
    assert list(cfg["handlers"]) == ["console"]


def test_dict_config_falls_back_to_info_for_unknown_level():
    # configure_logging() guards unknown LOG_LEVEL; the dict always carries a real level.
    cfg = _build_dict_config("INFO")
    assert cfg["root"]["level"] == "INFO"


def test_configure_logging_quiets_noisy_third_parties():
    reset_configured()
    configure_logging()
    for name in ("httpx", "google.genai", "urllib3", "uvicorn.access"):
        assert logging.getLogger(name).level == logging.WARNING
    reset_configured()


def test_configure_logging_is_idempotent():
    reset_configured()
    configure_logging()
    configure_logging()  # second call must be a no-op, not raise
    reset_configured()


def test_orchestrator_logs_submission_steps_and_completion(caplog, loader, case_input):
    """The INFO log tells the whole story of one claim: a submission line, a
    per-step line carrying its duration, and a completion line with the decision."""
    with caplog.at_level(logging.INFO, logger="app.core.orchestrator"):
        orch = Orchestrator(loader=loader, llm=MockClient())
        sub = ClaimSubmission.model_validate(case_input("TC004"))
        asyncio.run(orch.process(sub))

    messages = [r.getMessage() for r in caplog.records if r.name == "app.core.orchestrator"]
    text = "\n".join(messages)

    # Submission line names member + category + amount
    assert any("member=EMP001" in m and "category=CONSULTATION" in m for m in messages)
    # At least one per-step line carries a "(<n>ms)" duration
    assert any(re.search(r"\(\d+ms\)", m) for m in messages), text
    # Completion line carries the decision + confidence
    assert any("COMPLETED status=" in m and "confidence=" in m for m in messages), text
