"""Runtime-derived protocol continuity recovery state."""

from __future__ import annotations

from datetime import datetime, timezone


ACTIVE_STALE_SECONDS = 6 * 60 * 60
INCOMPLETE_OLD_SECONDS = 7 * 24 * 60 * 60


def derive_run_recovery_state(
    *,
    run_status: str,
    started_at: str,
    now: str,
    has_summary: bool,
    has_handoff: bool,
) -> str:
    age = _parse_utc(now) - _parse_utc(started_at)
    seconds = age.total_seconds()
    if run_status == "active" and seconds >= ACTIVE_STALE_SECONDS and not has_summary and not has_handoff:
        return "stale_active_run"
    if run_status == "incomplete" and seconds >= INCOMPLETE_OLD_SECONDS:
        return "old_incomplete_run"
    return ""


def _parse_utc(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
