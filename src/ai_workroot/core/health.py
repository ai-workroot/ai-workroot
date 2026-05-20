"""Core System Health model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HealthCheckResult:
    check_id: str
    status: str
    message: str

    def is_passing(self) -> bool:
        return self.status == "pass"
