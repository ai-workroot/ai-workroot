"""Active time projection runtime services."""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3


@dataclass(frozen=True)
class TimeEvent:
    event_id: str
    workroot_id: str
    subject_type: str
    subject_id: str
    event_type: str
    occurred_at: str
    time_range_start: str = ""
    time_range_end: str = ""
    source_ref: str = ""
    created_at: str = ""


def record_time_event(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    event_id: str,
    subject_type: str,
    subject_id: str,
    event_type: str,
    occurred_at: str,
    time_range_start: str = "",
    time_range_end: str = "",
    source_ref: str = "",
    created_at: str = "",
) -> TimeEvent:
    for name, value in {
        "workroot_id": workroot_id,
        "event_id": event_id,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "event_type": event_type,
        "occurred_at": occurred_at,
    }.items():
        if not value:
            raise ValueError(f"{name} is required")

    event = TimeEvent(
        event_id=event_id,
        workroot_id=workroot_id,
        subject_type=subject_type,
        subject_id=subject_id,
        event_type=event_type,
        occurred_at=occurred_at,
        time_range_start=time_range_start,
        time_range_end=time_range_end,
        source_ref=source_ref,
        created_at=created_at,
    )
    conn.execute(
        """
        INSERT INTO time_events (
          event_id, workroot_id, subject_type, subject_id, event_type,
          occurred_at, time_range_start, time_range_end, source_ref, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(event_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          subject_type=excluded.subject_type,
          subject_id=excluded.subject_id,
          event_type=excluded.event_type,
          occurred_at=excluded.occurred_at,
          time_range_start=excluded.time_range_start,
          time_range_end=excluded.time_range_end,
          source_ref=excluded.source_ref,
          created_at=excluded.created_at
        """,
        (
            event.event_id,
            event.workroot_id,
            event.subject_type,
            event.subject_id,
            event.event_type,
            event.occurred_at,
            event.time_range_start,
            event.time_range_end,
            event.source_ref,
            event.created_at,
        ),
    )
    conn.commit()
    return event


def query_time_events(
    conn: sqlite3.Connection,
    workroot_id: str,
    *,
    subject_type: str | None = None,
    subject_id: str | None = None,
    event_type: str | None = None,
    limit: int = 100,
) -> list[TimeEvent]:
    where = ["workroot_id = ?"]
    params: list[object] = [workroot_id]
    if subject_type is not None:
        where.append("subject_type = ?")
        params.append(subject_type)
    if subject_id is not None:
        where.append("subject_id = ?")
        params.append(subject_id)
    if event_type is not None:
        where.append("event_type = ?")
        params.append(event_type)
    params.append(limit)
    rows = conn.execute(
        f"""
        SELECT event_id, workroot_id, subject_type, subject_id, event_type,
               occurred_at, time_range_start, time_range_end, source_ref, created_at
        FROM time_events
        WHERE {" AND ".join(where)}
        ORDER BY occurred_at ASC, event_id ASC
        LIMIT ?
        """,
        params,
    ).fetchall()
    return [_time_event_from_row(row) for row in rows]


def _time_event_from_row(row: sqlite3.Row | tuple[object, ...]) -> TimeEvent:
    return TimeEvent(
        event_id=str(row[_column(row, "event_id", 0)]),
        workroot_id=str(row[_column(row, "workroot_id", 1)]),
        subject_type=str(row[_column(row, "subject_type", 2)]),
        subject_id=str(row[_column(row, "subject_id", 3)]),
        event_type=str(row[_column(row, "event_type", 4)]),
        occurred_at=str(row[_column(row, "occurred_at", 5)]),
        time_range_start=str(row[_column(row, "time_range_start", 6)] or ""),
        time_range_end=str(row[_column(row, "time_range_end", 7)] or ""),
        source_ref=str(row[_column(row, "source_ref", 8)] or ""),
        created_at=str(row[_column(row, "created_at", 9)] or ""),
    )


def _column(row: sqlite3.Row | tuple[object, ...], name: str, index: int) -> str | int:
    if isinstance(row, sqlite3.Row):
        return name
    return index
