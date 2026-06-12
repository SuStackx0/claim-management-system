from __future__ import annotations
import json
from app.models.domain import Member
from app.models.policy import Policy, PolicyView

class PolicyLoader:
    def __init__(self, policy: Policy, raw: dict):
        self.policy = policy
        self._raw = raw
        self._members = {m.member_id: m for m in policy.members}

    @classmethod
    def load(cls, path: str) -> "PolicyLoader":
        with open(path) as f:
            raw = json.load(f)
        return cls(Policy.model_validate(raw), raw)

    def rule(self, ref: str):
        """JSON-path lookup into the raw policy; ref is the trace's rule_ref."""
        node = self._raw
        for part in ref.split("."):
            if not isinstance(node, dict) or part not in node:
                raise KeyError(f"rule_ref not found in policy: {ref}")
            node = node[part]
        return node

    def view(self, category: str) -> PolicyView:
        key = category.lower()
        if key not in self.policy.opd_categories:
            raise KeyError(f"unknown category: {category}")
        reqs = self.policy.document_requirements.get(category.upper(), {})
        return PolicyView(
            category=category.upper(),
            rules=self.policy.opd_categories[key],
            required_docs=reqs.get("required", []),
            optional_docs=reqs.get("optional", []),
        )

    def member(self, member_id: str) -> Member | None:
        return self._members.get(member_id)

    def dependents_of(self, member_id: str) -> list[Member]:
        m = self._members.get(member_id)
        if not m:
            return []
        return [self._members[d] for d in m.dependents if d in self._members]
