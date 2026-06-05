"""State version helpers."""

from __future__ import annotations

import sqlite3
import time
from typing import Optional


def now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def bump_state_version(
    conn: sqlite3.Connection,
    workroot_id: str,
    scope: str,
    updated_at: Optional[str] = None,
    *,
    updated_by_event_id: Optional[str] = None,
    reason: Optional[str] = None,
) -> None:
    conn.execute(
        """
        INSERT INTO state_versions (workroot_id, scope, version, updated_at, updated_by_event_id, reason)
        VALUES (?, ?, 1, ?, ?, ?)
        ON CONFLICT(workroot_id, scope) DO UPDATE SET
          version=state_versions.version + 1,
          updated_at=excluded.updated_at,
          updated_by_event_id=excluded.updated_by_event_id,
          reason=excluded.reason
        """,
        (workroot_id, scope, updated_at or now_utc(), updated_by_event_id, reason),
    )
