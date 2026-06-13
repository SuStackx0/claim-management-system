"""
Tests for ui/helpers.py, ui/render.py, and ui/streamlit_app.py (syntax only).

AppTest (streamlit.testing.v1) hangs on Python 3.13 during server init — same
root cause as google-genai slow import. Strategy:
  - ui.helpers (get/post) tested directly with mocked httpx — no st import.
  - ui.render (render_decision/render_trace) tested by injecting a mock
    'streamlit' into sys.modules BEFORE importing the module. This is the same
    object.__new__ pattern used for GeminiClient: bypass the slow init entirely.
  - ui.streamlit_app is only syntax-checked (py_compile) — its module-level
    page logic cannot safely run outside a real Streamlit server.
"""
from __future__ import annotations
import importlib
import py_compile
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

UI_DIR = Path(__file__).resolve().parent.parent / "ui"


# ---------------------------------------------------------------------------
# ui/helpers.py — pure HTTP helpers, no Streamlit needed
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_get_calls_correct_url(self):
        from ui.helpers import get
        with patch("httpx.get") as mock_get:
            mock_get.return_value.json.return_value = {"ok": True}
            result = get("/members")
        url = mock_get.call_args[0][0]
        assert url.endswith("/members")
        assert result == {"ok": True}

    def test_post_calls_correct_url(self):
        from ui.helpers import post
        with patch("httpx.post") as mock_post:
            mock_post.return_value.json.return_value = {"status": "COMPLETED"}
            result = post("/claims", json={"x": 1})
        url = mock_post.call_args[0][0]
        assert url.endswith("/claims")
        assert result == {"status": "COMPLETED"}

    def test_get_uses_api_base_env(self, monkeypatch):
        monkeypatch.setenv("API_BASE_URL", "http://example.com:9000")
        import ui.helpers as h
        importlib.reload(h)
        with patch("httpx.get") as mock_get:
            mock_get.return_value.json.return_value = []
            h.get("/claims")
        assert mock_get.call_args[0][0] == "http://example.com:9000/claims"
        monkeypatch.delenv("API_BASE_URL", raising=False)
        importlib.reload(h)

    def test_get_timeout_is_120(self):
        from ui.helpers import get
        with patch("httpx.get") as mock_get:
            mock_get.return_value.json.return_value = {}
            get("/x")
        assert mock_get.call_args[1]["timeout"] == 120

    def test_post_timeout_is_300(self):
        from ui.helpers import post
        with patch("httpx.post") as mock_post:
            mock_post.return_value.json.return_value = {}
            post("/x")
        assert mock_post.call_args[1]["timeout"] == 300


# ---------------------------------------------------------------------------
# Syntax check for streamlit_app.py (fast, no Streamlit import)
# ---------------------------------------------------------------------------

def test_streamlit_app_compiles():
    py_compile.compile(str(UI_DIR / "streamlit_app.py"), doraise=True)


def test_render_py_compiles():
    py_compile.compile(str(UI_DIR / "render.py"), doraise=True)


# ---------------------------------------------------------------------------
# ui/render.py — inject mock streamlit before importing
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def mock_st():
    """
    Inject a MagicMock as 'streamlit' in sys.modules before importing ui.render.
    ui.render has no page-level logic — it just defines two functions and does
    `import streamlit as st`. With the mock in place, that import returns the
    MagicMock instantly (no Streamlit server init, no 200s hang).
    """
    _st = MagicMock()
    sys.modules["streamlit"] = _st

    # Remove any cached real module so we re-import with mock
    for key in list(sys.modules.keys()):
        if key in ("ui.render",):
            del sys.modules[key]

    import ui.render  # noqa: F401 — triggers the mock-bound import

    yield _st

    # Cleanup: remove mock so other test modules aren't affected
    sys.modules.pop("streamlit", None)
    sys.modules.pop("ui.render", None)


class TestRenderDecision:
    def test_stopped_calls_st_error(self, mock_st):
        mock_st.reset_mock()
        from ui.render import render_decision
        render_decision({
            "status": "STOPPED",
            "member_message": "Missing HOSPITAL_BILL",
            "trace": {},
        })
        mock_st.error.assert_called_once()

    def test_approved_calls_st_success(self, mock_st):
        mock_st.reset_mock()
        from ui.render import render_decision
        render_decision({
            "status": "COMPLETED",
            "decision": {
                "status": "APPROVED",
                "approved_amount": 1350,
                "confidence": 0.95,
                "member_message": "Claim approved.",
            },
            "trace": {},
        })
        mock_st.success.assert_called_once()

    def test_rejected_calls_st_error(self, mock_st):
        mock_st.reset_mock()
        from ui.render import render_decision
        render_decision({
            "status": "COMPLETED",
            "decision": {
                "status": "REJECTED",
                "approved_amount": 0,
                "confidence": 0.9,
                "member_message": "Pre-existing condition excluded.",
            },
            "trace": {},
        })
        mock_st.error.assert_called_once()

    def test_manual_review_calls_st_info(self, mock_st):
        mock_st.reset_mock()
        from ui.render import render_decision
        render_decision({
            "status": "COMPLETED",
            "decision": {
                "status": "MANUAL_REVIEW",
                "approved_amount": 0,
                "confidence": 0.4,
                "member_message": "Flagged for review.",
            },
            "trace": {},
        })
        mock_st.info.assert_called_once()

    def test_partial_calls_st_warning(self, mock_st):
        mock_st.reset_mock()
        from ui.render import render_decision
        render_decision({
            "status": "COMPLETED",
            "decision": {
                "status": "PARTIAL",
                "approved_amount": 800,
                "confidence": 0.8,
                "member_message": "Partial approval.",
            },
            "trace": {},
        })
        mock_st.warning.assert_called_once()

    def test_unknown_decision_status_falls_back_to_info(self, mock_st):
        mock_st.reset_mock()
        from ui.render import render_decision
        render_decision({
            "status": "COMPLETED",
            "decision": {
                "status": "UNKNOWN_STATUS",
                "approved_amount": 0,
                "confidence": 0.5,
                "member_message": "?",
            },
            "trace": {},
        })
        mock_st.info.assert_called_once()


class TestRenderTrace:
    def test_empty_trace_no_subheader(self, mock_st):
        mock_st.reset_mock()
        from ui.render import render_trace
        render_trace({})
        mock_st.subheader.assert_not_called()

    def test_empty_steps_list_no_subheader(self, mock_st):
        mock_st.reset_mock()
        from ui.render import render_trace
        render_trace({"steps": []})
        mock_st.subheader.assert_not_called()

    def test_with_steps_calls_subheader(self, mock_st):
        mock_st.reset_mock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        from ui.render import render_trace
        render_trace({"steps": [
            {"step": "1", "agent": "IntakeAgent", "status": "PASS",
             "duration_ms": 5, "checks": [], "confidence_entries": []},
        ]})
        mock_st.subheader.assert_called_once()

    def test_expander_called_per_step(self, mock_st):
        mock_st.reset_mock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        from ui.render import render_trace
        render_trace({"steps": [
            {"step": "1", "agent": "A", "status": "PASS", "duration_ms": 1,
             "checks": [], "confidence_entries": []},
            {"step": "2", "agent": "B", "status": "FAIL", "duration_ms": 2,
             "checks": [], "confidence_entries": []},
        ]})
        assert mock_st.expander.call_count == 2

    def test_pass_icon_in_expander_label(self, mock_st):
        mock_st.reset_mock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        from ui.render import render_trace
        render_trace({"steps": [
            {"step": "1", "agent": "A", "status": "PASS", "duration_ms": 3,
             "checks": [], "confidence_entries": []},
        ]})
        label = mock_st.expander.call_args[0][0]
        assert "✅" in label

    def test_fail_icon_in_expander_label(self, mock_st):
        mock_st.reset_mock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        from ui.render import render_trace
        render_trace({"steps": [
            {"step": "1", "agent": "A", "status": "FAIL", "duration_ms": 3,
             "checks": [], "confidence_entries": []},
        ]})
        label = mock_st.expander.call_args[0][0]
        assert "❌" in label

    def test_degraded_icon_in_expander_label(self, mock_st):
        mock_st.reset_mock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        from ui.render import render_trace
        render_trace({"steps": [
            {"step": "1", "agent": "A", "status": "DEGRADED", "duration_ms": 3,
             "checks": [], "confidence_entries": []},
        ]})
        label = mock_st.expander.call_args[0][0]
        assert "⚠️" in label

    def test_skipped_icon_in_expander_label(self, mock_st):
        mock_st.reset_mock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        from ui.render import render_trace
        render_trace({"steps": [
            {"step": "1", "agent": "A", "status": "SKIPPED", "duration_ms": 3,
             "checks": [], "confidence_entries": []},
        ]})
        label = mock_st.expander.call_args[0][0]
        assert "⏭️" in label

    def test_unknown_icon_in_expander_label(self, mock_st):
        mock_st.reset_mock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        from ui.render import render_trace
        render_trace({"steps": [
            {"step": "1", "agent": "A", "status": "UNKNOWN", "duration_ms": 3,
             "checks": [], "confidence_entries": []},
        ]})
        label = mock_st.expander.call_args[0][0]
        assert "•" in label

    def test_render_checks_with_rule_ref_and_details(self, mock_st):
        mock_st.reset_mock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        from ui.render import render_trace
        render_trace({"steps": [
            {"step": "1", "agent": "A", "status": "PASS", "duration_ms": 3,
             "checks": [
                 {"check": "PolicyCheck", "result": "PASS", "rule_ref": "R-101", "detail": {"info": "ok"}},
                 {"check": "NoRuleCheck", "result": "FAIL"}
             ], "confidence_entries": []},
        ]})
        markdown_calls = [args[0] for args, kwargs in mock_st.markdown.call_args_list]
        assert any("PolicyCheck" in call and "rule: `R-101`" in call for call in markdown_calls)
        assert any("NoRuleCheck" in call and "rule" not in call for call in markdown_calls)
        mock_st.json.assert_called_once_with({"info": "ok"}, expanded=False)

    def test_render_step_error(self, mock_st):
        mock_st.reset_mock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        from ui.render import render_trace
        render_trace({"steps": [
            {"step": "1", "agent": "A", "status": "FAIL", "duration_ms": 3,
             "checks": [], "error": {"message": "something failed"}, "confidence_entries": []},
        ]})
        mock_st.code.assert_called_once()
        code_arg = mock_st.code.call_args[0][0]
        assert "something failed" in code_arg

    def test_render_confidence_entries(self, mock_st):
        mock_st.reset_mock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
        from ui.render import render_trace
        render_trace({"steps": [
            {"step": "1", "agent": "A", "status": "PASS", "duration_ms": 3,
             "checks": [], "confidence_entries": [
                 {"factor": 0.9, "reason": "Reason 1"},
                 {"factor": 0.8, "reason": "Reason 2"}
             ]},
        ]})
        caption_calls = [args[0] for args, kwargs in mock_st.caption.call_args_list]
        assert len(caption_calls) == 2
        assert "confidence ×0.9 — Reason 1" in caption_calls
        assert "confidence ×0.8 — Reason 2" in caption_calls

