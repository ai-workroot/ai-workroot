"""Exchange lease and state version helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import sqlite3
import time
from typing import Any, Optional
import uuid

from ai_workroot.protocol.directives import resync_required


def now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass(frozen=True)
class LeaseValidationResult:
    ok: bool
    lease: Optional[dict[str, Any]] = None
    error: Optional[dict[str, Any]] = None
    directive: Optional[dict[str, Any]] = None


def load_state_versions(conn: sqlite3.Connection, workroot_id: str, scopes: list[str]) -> dict[str, int]:
    versions: dict[str, int] = {}
    for scope in scopes:
        row = conn.execute(
            "SELECT version FROM state_versions WHERE workroot_id = ? AND scope = ?",
            (workroot_id, scope),
        ).fetchone()
        versions[scope] = int(row[0]) if row else 0
    return versions


def bump_state_version(
    conn: sqlite3.Connection, workroot_id: str, scope: str, updated_at: Optional[str] = None
) -> None:
    current = load_state_versions(conn, workroot_id, [scope])[scope]
    conn.execute(
        """
        INSERT INTO state_versions (workroot_id, scope, version, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(workroot_id, scope) DO UPDATE SET
          version=excluded.version,
          updated_at=excluded.updated_at
        """,
        (workroot_id, scope, current + 1, updated_at or now_utc()),
    )


def create_lease(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    scope: str,
    task_id: Optional[str],
    run_id: Optional[str],
    allowed_events: list[str],
    required_before_stop: Optional[list[str]] = None,
    issued_at: Optional[str] = None,
    expires_at: Optional[str] = None,
    lease_id: Optional[str] = None,
) -> dict[str, Any]:
    issued = issued_at or now_utc()
    expires = expires_at or _default_expiry(issued)
    scopes = _observed_scopes(task_id=task_id, run_id=run_id)
    observed_versions = load_state_versions(conn, workroot_id, scopes)
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
        "status": "active",
    }
    conn.execute(
        """
        INSERT INTO exchange_leases (
          lease_id, workroot_id, scope, task_id, run_id, observed_versions_json,
          allowed_events_json, required_before_stop_json, status, issued_at, expires_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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


def load_lease(conn: sqlite3.Connection, lease_id: str) -> Optional[dict[str, Any]]:
    row = conn.execute(
        """
        SELECT lease_id, workroot_id, scope, task_id, run_id, observed_versions_json,
               allowed_events_json, required_before_stop_json, status, issued_at, expires_at
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
        "status": row[8],
        "issued_at": row[9],
        "expires_at": row[10],
    }


def _lease_error(code: str) -> LeaseValidationResult:
    return LeaseValidationResult(
        ok=False,
        error={"code": code, "message": code, "details": {}},
        directive=resync_required(),
    )


def _observed_scopes(*, task_id: Optional[str], run_id: Optional[str]) -> list[str]:
    scopes = ["workroot", "context"]
    if task_id:
        scopes.append(f"task:{task_id}")
    if run_id:
        scopes.append(f"run:{run_id}")
    return scopes


def _default_expiry(issued_at: str) -> str:
    issued = datetime.strptime(issued_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (issued + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
