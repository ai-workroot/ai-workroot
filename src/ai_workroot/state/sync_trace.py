"""Runtime sync-packet diagnostics."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import uuid

from ai_workroot.state.environment import utc_now
from ai_workroot.state.jsonl import append_jsonl


SYNC_PACKET_LOG_RELATIVE_PATH = Path("logs/sync-packets.jsonl")


def record_sync_packet_trace(
    *,
    state_directory: Path,
    workroot_id: str,
    request_id: str,
    agent: str,
    transport: str,
    focus: str,
    confidence: str,
    action: str,
    shape: str,
    packet_bytes: int,
    task_bound: bool,
    run_bound: bool,
    compact: bool = True,
    trimmed_open_items: int = 0,
    trimmed_done_items: int = 0,
    occurred_at: str | None = None,
) -> None:
    append_jsonl(
        Path(state_directory) / SYNC_PACKET_LOG_RELATIVE_PATH,
        {
            "eventId": f"sync_packet_{uuid.uuid4().hex}",
            "workrootId": workroot_id,
            "requestId": request_id,
            "agent": agent,
            "transport": transport,
            "focus": focus,
            "confidence": confidence,
            "action": action,
            "shape": shape,
            "packetBytes": packet_bytes,
            "taskBound": task_bound,
            "runBound": run_bound,
            "compact": compact,
            "trimmedOpenItems": max(0, trimmed_open_items),
            "trimmedDoneItems": max(0, trimmed_done_items),
            "occurredAt": occurred_at or utc_now(),
        },
    )


def sync_packet_trim_counts(response: dict[str, Any]) -> tuple[int, int]:
    view = response.get("workroot_view") if isinstance(response.get("workroot_view"), dict) else {}
    open_items = view.get("open_items")
    done_items = view.get("recent_done_items")
    open_count = len(open_items) if isinstance(open_items, list) else 0
    done_count = len(done_items) if isinstance(done_items, list) else 0
    return max(0, open_count - 3), max(0, done_count - 3)
