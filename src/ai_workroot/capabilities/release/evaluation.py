"""Release Control target evaluation."""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Iterable

from ai_workroot.capabilities.release.model import ReleaseTargetRef


STRICT_LEVELS = {"deleted", "redacted", "safety-sensitive"}
TOMBSTONE_LEVEL = "tombstone"


@dataclass(frozen=True)
class ReleaseEvaluation:
    level: str
    matched_targets: tuple[ReleaseTargetRef, ...]

    @property
    def strictly_protected(self) -> bool:
        return self.level in STRICT_LEVELS

    @property
    def tombstone(self) -> bool:
        return self.level == TOMBSTONE_LEVEL


def evaluate_release_targets(
    conn: sqlite3.Connection,
    workroot_id: str,
    refs: Iterable[ReleaseTargetRef],
) -> ReleaseEvaluation:
    unique_refs = tuple(_dedupe_refs(refs))
    level = "none"
    matched: list[ReleaseTargetRef] = []
    for ref in unique_refs:
        for found_level in _levels_for_target(conn, workroot_id, ref):
            normalized = _normalize_release_level(found_level)
            if _release_level_rank(normalized) > _release_level_rank(level):
                level = normalized
            matched.append(ref)
    return ReleaseEvaluation(level=level, matched_targets=tuple(_dedupe_refs(matched)))


def _levels_for_target(conn: sqlite3.Connection, workroot_id: str, ref: ReleaseTargetRef) -> tuple[str, ...]:
    levels: list[str] = []
    levels.extend(
        _query_levels(
            conn,
            """
            SELECT release_level
            FROM release_records
            WHERE workroot_id = ? AND target_type = ? AND target_id = ?
            """,
            (workroot_id, ref.target_type, ref.target_id),
        )
    )
    for table, level in (
        ("deletion_records", "deleted"),
        ("redactions", "redacted"),
        ("tombstones", "tombstone"),
    ):
        if _target_exists(conn, table, workroot_id, ref):
            levels.append(level)
    return tuple(levels)


def _query_levels(conn: sqlite3.Connection, sql: str, params: tuple[str, ...]) -> tuple[str, ...]:
    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        return ()
    return tuple(str(row[0] or "") for row in rows)


def _target_exists(conn: sqlite3.Connection, table: str, workroot_id: str, ref: ReleaseTargetRef) -> bool:
    try:
        row = conn.execute(
            f"""
            SELECT 1
            FROM {table}
            WHERE workroot_id = ? AND target_type = ? AND target_id = ?
            LIMIT 1
            """,
            (workroot_id, ref.target_type, ref.target_id),
        ).fetchone()
    except sqlite3.OperationalError:
        return False
    return row is not None


def _normalize_release_level(release_level: str) -> str:
    value = (release_level or "").lower().strip().replace("_", "-")
    if value in {"sensitive", "safety-sensitive"}:
        return "safety-sensitive"
    if value == "archive":
        return "archived"
    return value


def _release_level_rank(release_level: str) -> int:
    return {
        "deleted": 6,
        "redacted": 5,
        "safety-sensitive": 4,
        "tombstone": 3,
        "archived": 2,
        "quiet": 1,
        "none": 0,
        "": 0,
    }.get(_normalize_release_level(release_level), 0)


def _dedupe_refs(refs: Iterable[ReleaseTargetRef]) -> list[ReleaseTargetRef]:
    seen: set[tuple[str, str]] = set()
    deduped: list[ReleaseTargetRef] = []
    for ref in refs:
        key = (ref.target_type, ref.target_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ref)
    return deduped
