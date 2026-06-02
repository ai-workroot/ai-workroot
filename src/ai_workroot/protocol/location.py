"""Workroot location confidence for non-blocking commits."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from ai_workroot.protocol.lease import load_lease, now_utc
from ai_workroot.state.layout import workroot_sqlite_path
from ai_workroot.state.registry import find_workroot_by_cwd, list_workroots
from ai_workroot.state.sqlite import initialize_workroot_sqlite


@dataclass(frozen=True)
class LocatedWorkroot:
    confidence: str
    record: dict[str, str] | None
    sqlite_path: Path | None
    lease: dict[str, object] | None = None
    reason: str = ""

    @property
    def located(self) -> bool:
        return self.record is not None and self.sqlite_path is not None


def locate_for_commit(
    *,
    lease_id: str | None,
    cwd: str | None,
    workroot_id: str | None,
    ai_workroot_home: Path | str | None = None,
) -> LocatedWorkroot:
    explicit = _locate_explicit(cwd=cwd, workroot_id=workroot_id, ai_workroot_home=ai_workroot_home)
    if explicit is not None and explicit.confidence == "no_location":
        return explicit

    lease_located = _locate_by_lease(lease_id, ai_workroot_home=ai_workroot_home) if lease_id else None
    if explicit is not None and lease_located is not None and explicit.record != lease_located.record:
        return LocatedWorkroot("no_location", None, None, None, "conflicting_locators")
    if explicit is not None:
        return explicit
    if lease_located is not None:
        return lease_located
    return LocatedWorkroot("no_location", None, None, None, "missing_workroot_locator")


def _locate_explicit(
    *,
    cwd: str | None,
    workroot_id: str | None,
    ai_workroot_home: Path | str | None,
) -> LocatedWorkroot | None:
    if workroot_id:
        for record in list_workroots(ai_workroot_home=ai_workroot_home):
            if record["workrootId"] == workroot_id:
                sqlite_path = workroot_sqlite_path(Path(record["stateDirectory"]))
                initialize_workroot_sqlite(sqlite_path)
                return LocatedWorkroot("strong_location", record, sqlite_path, None, "workroot_id")
        return LocatedWorkroot("no_location", None, None, None, "unknown_workroot_id")
    if cwd:
        try:
            record = find_workroot_by_cwd(Path(cwd), ai_workroot_home=ai_workroot_home)
        except ValueError:
            return LocatedWorkroot("no_location", None, None, None, "cwd_not_registered")
        sqlite_path = workroot_sqlite_path(Path(record["stateDirectory"]))
        initialize_workroot_sqlite(sqlite_path)
        return LocatedWorkroot("strong_location", record, sqlite_path, None, "cwd")
    return None


def _locate_by_lease(lease_id: str | None, *, ai_workroot_home: Path | str | None) -> LocatedWorkroot | None:
    if not lease_id:
        return None
    for record in list_workroots(ai_workroot_home=ai_workroot_home):
        sqlite_path = workroot_sqlite_path(Path(record["stateDirectory"]))
        initialize_workroot_sqlite(sqlite_path)
        with sqlite3.connect(sqlite_path) as conn:
            lease = load_lease(conn, lease_id)
        if lease is not None:
            active = lease.get("status") == "active" and str(lease.get("expires_at") or "") >= now_utc()
            confidence = "strong_location" if active else "weak_location"
            return LocatedWorkroot(confidence, record, sqlite_path, lease, "lease")
    return None
