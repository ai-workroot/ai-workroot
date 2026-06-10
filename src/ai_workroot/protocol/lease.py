"""Exchange lease and state version helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import sqlite3
from typing import Any, Optional
import uuid

from ai_workroot.protocol.directives import resync_required
from ai_workroot.state.versions import load_state_versions, now_utc


@dataclass(frozen=True)
class LeaseValidationResult:
    ok: bool
    lease: Optional[dict[str, Any]] = None
    error: Optional[dict[str, Any]] = None
    directive: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class LeaseSafetyDecision:
    status: str
    lease: Optional[dict[str, Any]]
    warnings: tuple[str, ...] = ()
    error_code: str = ""

    @property
    def can_project(self) -> bool:
        return self.status == "applied"


def create_lease(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    scope: str,
    task_id: Optional[str],
    run_id: Optional[str],
    allowed_events: list[str],
    required_before_stop: Optional[list[str]] = None,
    policy: Optional[dict[str, Any]] = None,
    issued_at: Optional[str] = None,
    expires_at: Optional[str] = None,
    lease_id: Optional[str] = None,
) -> dict[str, Any]:
    issued = issued_at or now_utc()
    expires = expires_at or _default_expiry(issued)
    scopes = _observed_scopes(task_id=task_id, run_id=run_id)
    observed_versions = load_state_versions(conn, workroot_id, scopes)
    normalized_policy = _normalize_policy(policy)
    lease = {
        "lease_id": lease_id or f"lease-{uuid.uuid4().hex}",
        "scope": scope,
        "workroot_id": workroot_id,
        "task_id": task_id,
        "run_id": run_id,
        "issued_at": issued,
        "expires_at": expires,
        "observed_versions": observed_versions,
        "allowed_events": list(allowed_events),
        "required_before_stop": list(required_before_stop or []),
        "policy": normalized_policy,
        "status": "active",
    }
    conn.execute(
        """
        INSERT INTO exchange_leases (
          lease_id, workroot_id, scope, task_id, run_id, observed_versions_json,
          allowed_events_json, required_before_stop_json, policy_json, status, issued_at, expires_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            lease["lease_id"],
            workroot_id,
            scope,
            task_id,
            run_id,
            json.dumps(observed_versions, sort_keys=True),
            json.dumps(allowed_events, sort_keys=True),
            json.dumps(required_before_stop or [], sort_keys=True),
            json.dumps(normalized_policy, sort_keys=True),
            "active",
            issued,
            expires,
        ),
    )
    return lease


def validate_lease(
    conn: sqlite3.Connection,
    lease_id: str,
    *,
    events: list[dict[str, Any]],
    now: Optional[str] = None,
) -> LeaseValidationResult:
    lease = load_lease(conn, lease_id)
    if lease is None:
        return _lease_error("lease_not_found")
    if lease["status"] != "active":
        return _lease_error("lease_not_active")
    checked_at = now or now_utc()
    if checked_at > lease["expires_at"]:
        conn.execute("UPDATE exchange_leases SET status = 'expired' WHERE lease_id = ?", (lease_id,))
        return _lease_error("lease_expired")
    allowed_events = set(lease["allowed_events"])
    for event in events:
        if event.get("kind") not in allowed_events:
            return _lease_error("event_not_allowed")
    current_versions = load_state_versions(
        conn,
        str(lease["workroot_id"]),
        list(lease["observed_versions"].keys()),
    )
    if current_versions != lease["observed_versions"]:
        return _lease_error("state_conflict")
    return LeaseValidationResult(ok=True, lease=lease)


def decide_lease_safety(
    conn: sqlite3.Connection,
    lease_id: str,
    *,
    workroot_id: str,
    events: list[dict[str, Any]],
    now: Optional[str] = None,
) -> LeaseSafetyDecision:
    lease = load_lease(conn, lease_id)
    if lease is None:
        return LeaseSafetyDecision(status="rejected", lease=None, error_code="lease_not_found")
    if lease["workroot_id"] != workroot_id:
        return LeaseSafetyDecision(status="rejected", lease=lease, error_code="lease_workroot_mismatch")

    allowed_events = set(lease["allowed_events"])
    for event in events:
        if event.get("kind") not in allowed_events:
            return LeaseSafetyDecision(status="rejected", lease=lease, error_code="event_not_allowed")

    current_versions = load_state_versions(conn, workroot_id, list(lease["observed_versions"].keys()))
    versions_match = current_versions == lease["observed_versions"]
    checked_at = now or now_utc()
    expired = lease["status"] == "expired" or checked_at > str(lease["expires_at"] or "")
    active = lease["status"] == "active"

    if not versions_match:
        return LeaseSafetyDecision(status="resync_required", lease=lease, error_code="state_conflict")
    if active and not expired:
        return LeaseSafetyDecision(status="applied", lease=lease)
    if expired and _all_events_safe_after_expiry(events):
        conn.execute("UPDATE exchange_leases SET status = 'expired' WHERE lease_id = ?", (lease_id,))
        return LeaseSafetyDecision(
            status="applied",
            lease=lease,
            warnings=("lease_expired_safe_projection",),
            error_code="lease_expired",
        )
    if expired:
        conn.execute("UPDATE exchange_leases SET status = 'expired' WHERE lease_id = ?", (lease_id,))
        return LeaseSafetyDecision(status="resync_required", lease=lease, error_code="lease_expired")
    return LeaseSafetyDecision(status="rejected", lease=lease, error_code="lease_not_active")


def load_lease(conn: sqlite3.Connection, lease_id: str) -> Optional[dict[str, Any]]:
    row = conn.execute(
        """
        SELECT lease_id, workroot_id, scope, task_id, run_id, observed_versions_json,
               allowed_events_json, required_before_stop_json, policy_json, status, issued_at, expires_at
        FROM exchange_leases
        WHERE lease_id = ?
        """,
        (lease_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "lease_id": row[0],
        "workroot_id": row[1],
        "scope": row[2],
        "task_id": row[3],
        "run_id": row[4],
        "observed_versions": json.loads(row[5]),
        "allowed_events": json.loads(row[6]),
        "required_before_stop": json.loads(row[7]),
        "policy": json.loads(row[8] or "{}"),
        "status": row[9],
        "issued_at": row[10],
        "expires_at": row[11],
    }


def _lease_error(code: str) -> LeaseValidationResult:
    return LeaseValidationResult(
        ok=False,
        error={"code": code, "message": code, "details": {}},
        directive=resync_required(),
    )


def _observed_scopes(*, task_id: Optional[str], run_id: Optional[str]) -> list[str]:
    scopes = ["workroot", "event_log"]
    if task_id:
        scopes.append(f"task:{task_id}")
        scopes.append(f"context:task:{task_id}")
    if run_id:
        scopes.append(f"run:{run_id}")
    return scopes


def _normalize_policy(policy: Optional[dict[str, Any]]) -> dict[str, str]:
    if not isinstance(policy, dict):
        return {}
    normalized: dict[str, str] = {}
    allowed = {
        "expected_start_work_persistence",
        "expected_task_role",
        "source",
    }
    for key, value in policy.items():
        if key not in allowed:
            continue
        text = str(value or "").strip()
        if text:
            normalized[key] = text
    return normalized


def _all_events_safe_after_expiry(events: list[dict[str, Any]]) -> bool:
    return bool(events) and all(event.get("kind") in {"progress", "handoff"} for event in events)


def _default_expiry(issued_at: str) -> str:
    issued = datetime.strptime(issued_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (issued + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
