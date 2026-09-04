"""Short-lived, in-memory mutation plans for Canvas writes."""

from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


PLAN_TTL = timedelta(minutes=10)


def fingerprint(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()


@dataclass(slots=True)
class Mutation:
    method: str
    endpoint: str
    data: dict[str, Any] | None = None
    json_data: dict[str, Any] | None = None
    label: str | None = None


@dataclass(slots=True)
class Precondition:
    endpoint: str
    fingerprint: str
    params: dict[str, Any] | None = None


@dataclass(slots=True)
class PendingPlan:
    token: str
    action: str
    summary: str
    preview: dict[str, Any]
    mutations: list[Mutation]
    preconditions: list[Precondition] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    destructive: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + PLAN_TTL
    )

    def public(self) -> dict[str, Any]:
        return {
            "plan_token": self.token,
            "action": self.action,
            "summary": self.summary,
            "preview": self.preview,
            "warnings": self.warnings,
            "destructive": self.destructive,
            "mutation_count": len(self.mutations),
            "targets": [
                {
                    "method": mutation.method,
                    "endpoint": mutation.endpoint,
                    **({"label": mutation.label} if mutation.label else {}),
                }
                for mutation in self.mutations
            ],
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "next_step": "Call canvas_apply_change with this plan_token and confirm=true.",
        }


class PlanStore:
    def __init__(self) -> None:
        self._plans: dict[str, PendingPlan] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        *,
        action: str,
        summary: str,
        preview: dict[str, Any],
        mutations: list[Mutation],
        preconditions: list[Precondition] | None = None,
        warnings: list[str] | None = None,
        destructive: bool = False,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        plan = PendingPlan(
            token=secrets.token_urlsafe(24),
            action=action,
            summary=summary,
            preview=preview,
            mutations=mutations,
            preconditions=preconditions or [],
            warnings=warnings or [],
            destructive=destructive,
            created_at=now,
            expires_at=now + PLAN_TTL,
        )
        async with self._lock:
            self._purge_expired(now)
            self._plans[plan.token] = plan
        return plan.public()

    async def consume(self, token: str) -> PendingPlan:
        now = datetime.now(timezone.utc)
        async with self._lock:
            self._purge_expired(now)
            plan = self._plans.pop(token, None)
        if plan is None:
            raise ValueError("Plan token is invalid, expired, or has already been used")
        return plan

    async def append_mutations(
        self, token: str, mutations: list[Mutation]
    ) -> dict[str, Any]:
        """Append dependent work while a newly-created plan is still locked."""
        async with self._lock:
            plan = self._plans.get(token)
            if plan is None:
                raise ValueError("Plan token is invalid or expired")
            plan.mutations.extend(mutations)
            return plan.public()

    def _purge_expired(self, now: datetime) -> None:
        expired = [key for key, plan in self._plans.items() if plan.expires_at <= now]
        for key in expired:
            self._plans.pop(key, None)


plan_store = PlanStore()
