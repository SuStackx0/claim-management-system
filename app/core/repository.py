from __future__ import annotations
import json, sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator
from app.models.domain import ClaimOutcome, ClaimSubmission

_SCHEMA = """
CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    member_id TEXT NOT NULL,
    category TEXT NOT NULL,
    treatment_date TEXT NOT NULL,
    claimed_amount INTEGER NOT NULL,
    status TEXT NOT NULL,
    decision_status TEXT,
    approved_amount INTEGER,
    confidence REAL,
    created_at TEXT NOT NULL,
    submission_json TEXT NOT NULL,
    outcome_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_claims_member ON claims(member_id, treatment_date);
"""


class Repository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        with self._conn() as c:
            c.executescript(_SCHEMA)

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def save(self, sub: ClaimSubmission, outcome: ClaimOutcome) -> None:
        d = outcome.decision
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO claims VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (outcome.claim_id, sub.member_id, sub.claim_category, str(sub.treatment_date),
                 sub.claimed_amount, outcome.status,
                 d.status if d else None, d.approved_amount if d else None,
                 d.confidence if d else None,
                 datetime.now(timezone.utc).isoformat(),
                 sub.model_dump_json(exclude={"documents": {"__all__": {"file_bytes"}}}),
                 outcome.model_dump_json()))

    def get(self, claim_id: str) -> dict | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM claims WHERE claim_id=?", (claim_id,)).fetchone()
        if row is None:
            return None
        out = json.loads(row["outcome_json"])
        out["member_id"] = row["member_id"]
        return out

    def list_claims(self) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT claim_id, member_id, category, treatment_date, claimed_amount, "
                "status, decision_status, approved_amount, confidence, created_at "
                "FROM claims ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
