"""Active time projection runtime services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class TimeEvent:
    event_id: str
    workroot_id: str
    subject_type: str
    subject_id: str
    event_type: str
    occurred_at: str
    timezone_id: str = "UTC"
    local_date: str = ""
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
    timezone_id: str = "UTC",
    local_date: str = "",
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
    timezone_id = _valid_timezone_or_utc(timezone_id)
    local_date = local_date or _local_date_for(occurred_at, timezone_id)

    event = TimeEvent(
        event_id=event_id,
        workroot_id=workroot_id,
        subject_type=subject_type,
        subject_id=subject_id,
        event_type=event_type,
        occurred_at=occurred_at,
        timezone_id=timezone_id,
        local_date=local_date,
        time_range_start=time_range_start,
        time_range_end=time_range_end,
        source_ref=source_ref,
        created_at=created_at,
    )
    conn.execute(
        """
        INSERT INTO time_events (
          event_id, workroot_id, subject_type, subject_id, event_type,
          occurredAt, timezoneId, localDate, timeRangeStart,
          timeRangeEnd, source_ref, createdAt
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(event_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          subject_type=excluded.subject_type,
          subject_id=excluded.subject_id,
          event_type=excluded.event_type,
          occurredAt=excluded.occurredAt,
          timezoneId=excluded.timezoneId,
          localDate=excluded.localDate,
          timeRangeStart=excluded.timeRangeStart,
          timeRangeEnd=excluded.timeRangeEnd,
          source_ref=excluded.source_ref,
          createdAt=excluded.createdAt
        """,
        (
            event.event_id,
            event.workroot_id,
            event.subject_type,
            event.subject_id,
            event.event_type,
            event.occurred_at,
            event.timezone_id,
            event.local_date,
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
               occurredAt, timezoneId, localDate, timeRangeStart,
               timeRangeEnd, source_ref, createdAt
        FROM time_events
        WHERE {" AND ".join(where)}
        ORDER BY occurredAt ASC, event_id ASC
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
        occurred_at=str(row[_column(row, "occurredAt", 5)]),
        timezone_id=str(row[_column(row, "timezoneId", 6)] or "UTC"),
        local_date=str(row[_column(row, "localDate", 7)] or ""),
        time_range_start=str(row[_column(row, "timeRangeStart", 8)] or ""),
        time_range_end=str(row[_column(row, "timeRangeEnd", 9)] or ""),
        source_ref=str(row[_column(row, "source_ref", 10)] or ""),
        created_at=str(row[_column(row, "createdAt", 11)] or ""),
    )


def _column(row: sqlite3.Row | tuple[object, ...], name: str, index: int) -> str | int:
    if isinstance(row, sqlite3.Row):
        return name
    return index


def _local_date_for(utc_value: str, timezone_id: str) -> str:
    normalized = utc_value[:-1] + "+00:00" if utc_value.endswith("Z") else utc_value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(ZoneInfo(timezone_id)).date().isoformat()


def _valid_timezone_or_utc(value: str) -> str:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError:
        return "UTC"
    return value
