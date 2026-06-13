"""
Pure helper functions for the Streamlit UI.
Importable without a running Streamlit session — safe to unit-test directly.
"""
from __future__ import annotations
import os
import httpx

API = os.getenv("API_BASE_URL", "http://localhost:8000")


def get(path: str):
    return httpx.get(f"{API}{path}", timeout=120).json()


def post(path: str, **kw):
    return httpx.post(f"{API}{path}", timeout=300, **kw).json()
