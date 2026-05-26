# Workroot Agent Protocol P0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the 0.9.531 Workroot Agent Protocol P0 loop: `sync -> lease -> commit(intent) -> task/run projection -> commit(progress) -> commit(handoff) -> next sync can continue`.

**Architecture:** Add a dedicated `protocol/` control-plane module above domain capabilities and below transport adapters. `sync` is read-only for semantic facts and only creates an exchange lease; `commit` is the only Agent fact entry and writes append-only `protocol_events` before deterministic projections.

**Tech Stack:** Python 3.9 standard library, `sqlite3`, `argparse`, `dataclasses`, `unittest`, existing `ai_workroot.state` and command-first source layout.

---

## Reference Spec

- Final Spec: `/Users/zeer/workroot_agent_protocol_docs_bundle/workroot_agent_protocol_v1_spec_0.9.531_final.md`
- Branch: `feat/0.9.531-agent-protocol-task-continuity`
- SQLite path remains: `<stateDirectory>/cache/workroot.sqlite`
- Runtime views path: `<stateDirectory>/runtime`

## File Map

- Create: `src/ai_workroot/protocol/__init__.py`  
  Public protocol package marker.
- Create: `src/ai_workroot/protocol/errors.py`  
  Error codes and error response helpers.
- Create: `src/ai_workroot/protocol/model.py`  
  Sync/commit request and response dataclasses plus validation.
- Create: `src/ai_workroot/protocol/events.py`  
  Event envelope validation and canonical request hashing helpers.
- Create: `src/ai_workroot/protocol/directives.py`  
  Directive builders and directive enum enforcement.
- Create: `src/ai_workroot/protocol/lease.py`  
  Exchange lease creation, loading, validation, and state version helpers.
- Create: `src/ai_workroot/protocol/controller.py`  
  `sync()` and `commit()` orchestration.
- Create: `src/ai_workroot/protocol/projections.py`  
  P0 projections for `intent`, `progress`, `handoff`, and `state`.
- Create: `src/ai_workroot/commands/agent_exchange.py`  
  CLI command adapter to protocol controller.
- Create: `src/ai_workroot/context/continuity.py`  
  Minimal continuity package loader for summary and handoff.
- Modify: `src/ai_workroot/cli/main.py`  
  Add `agent exchange`, `agent sync`, and `agent commit`.
- Modify: `src/ai_workroot/state/sqlite.py`  
  Add 0.9.531 protocol schema and required table validation.
- Modify: `src/ai_workroot/work/model.py`  
  Update Task/TaskRun model names and fields for P0.
- Modify: `src/ai_workroot/work/operations.py`  
  Add transaction-friendly helpers or avoid using auto-committing helpers from protocol projections.
- Modify: `pyproject.toml`  
  Bump package version to `0.9.531`.
- Create: `tests/unit/test_protocol_models.py`
- Create: `tests/unit/test_protocol_lease.py`
- Create: `tests/unit/test_protocol_idempotency.py`
- Create: `tests/unit/test_protocol_controller.py`
- Create: `tests/unit/test_protocol_projections.py`
- Create: `tests/integration/test_agent_protocol_loop.py`
- Modify: `tests/unit/test_import_boundaries.py`
- Modify: `tests/smoke/test_cli_discovery.py`
- Modify: `tests/smoke/test_package_entrypoint.py`

## Tasks

### Task 1: Version And CLI Discovery Baseline

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/ai_workroot/cli/main.py`
- Modify: `tests/smoke/test_package_entrypoint.py`
- Modify: `tests/smoke/test_cli_discovery.py`

- [ ] **Step 1: Write failing version assertion**

Add or update a test in `tests/smoke/test_package_entrypoint.py`:

```python
def test_package_version_reports_0_9_531() -> None:
    result = run_cli(["--version"])
    assert result.returncode == 0
    assert result.stdout.strip() == "AI Workroot 0.9.531"
```

- [ ] **Step 2: Run the version test**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.smoke.test_package_entrypoint -v
```

Expected: FAIL because the CLI still reports `AI Workroot 0.9.530`.

- [ ] **Step 3: Bump version**

Change:

```toml
version = "0.9.531"
```

Change `src/ai_workroot/cli/main.py`:

```python
if args.version:
    print("AI Workroot 0.9.531")
    return 0
```

- [ ] **Step 4: Verify version**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.smoke.test_package_entrypoint -v
PYTHONPATH=src python3 -m ai_workroot --version
```

Expected: PASS and `AI Workroot 0.9.531`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/ai_workroot/cli/main.py tests/smoke/test_package_entrypoint.py
git commit -m "feat: bump workroot protocol version to 0.9.531"
```

### Task 2: Protocol Model And Validation

**Files:**
- Create: `src/ai_workroot/protocol/__init__.py`
- Create: `src/ai_workroot/protocol/errors.py`
- Create: `src/ai_workroot/protocol/model.py`
- Create: `src/ai_workroot/protocol/events.py`
- Create: `tests/unit/test_protocol_models.py`

- [ ] **Step 1: Write protocol model tests**

Create `tests/unit/test_protocol_models.py`:

```python
from __future__ import annotations

import unittest

from ai_workroot.protocol.errors import ProtocolError
from ai_workroot.protocol.events import validate_event_envelope
from ai_workroot.protocol.model import SyncRequest, CommitRequest


class ProtocolModelTest(unittest.TestCase):
    def test_sync_request_requires_protocol_version(self) -> None:
        with self.assertRaisesRegex(ProtocolError, "missing_protocol_version"):
            SyncRequest.from_dict({"request_id": "req-1", "agent": {"name": "codex", "transport": "cli"}, "cwd": ".", "reason": "startup"})

    def test_sync_request_requires_locator(self) -> None:
        with self.assertRaisesRegex(ProtocolError, "missing_workroot_locator"):
            SyncRequest.from_dict(
                {
                    "protocol_version": "workroot.v1",
                    "request_id": "req-1",
                    "agent": {"name": "codex", "transport": "cli"},
                    "reason": "startup",
                }
            )

    def test_invalid_sync_reason_rejected(self) -> None:
        with self.assertRaisesRegex(ProtocolError, "invalid_sync_reason"):
            SyncRequest.from_dict(
                {
                    "protocol_version": "workroot.v1",
                    "request_id": "req-1",
                    "agent": {"name": "codex", "transport": "cli"},
                    "cwd": ".",
                    "reason": "bad",
                }
            )

    def test_commit_requires_events(self) -> None:
        with self.assertRaisesRegex(ProtocolError, "empty_event_batch"):
            CommitRequest.from_dict(
                {
                    "protocol_version": "workroot.v1",
                    "request_id": "req-commit",
                    "exchange_lease_id": "lease-1",
                    "idempotency_key": "key-1",
                    "events": [],
                }
            )

    def test_unknown_event_kind_rejected(self) -> None:
        with self.assertRaisesRegex(ProtocolError, "invalid_event_kind"):
            validate_event_envelope(
                {
                    "event_id": "evt-1",
                    "kind": "unknown",
                    "schema_version": "unknown.v1",
                    "occurred_at": "2026-05-26T10:00:00Z",
                    "source": {},
                    "confirmation": {},
                    "payload": {},
                    "evidence": [],
                }
            )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_models -v
```

Expected: FAIL because `ai_workroot.protocol` does not exist.

- [ ] **Step 3: Add protocol errors**

Create `src/ai_workroot/protocol/errors.py`:

```python
"""Workroot Agent Protocol errors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ProtocolError(ValueError):
    def __init__(self, code: str, message: str | None = None, details: dict[str, Any] | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.details = details or {}


@dataclass(frozen=True)
class ErrorResponse:
    code: str
    message: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}
```

- [ ] **Step 4: Add protocol package marker**

Create `src/ai_workroot/protocol/__init__.py`:

```python
"""Workroot Agent Protocol control plane."""
```

- [ ] **Step 5: Add event validation**

Create `src/ai_workroot/protocol/events.py`:

```python
"""Protocol event envelope validation and hashing."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from ai_workroot.protocol.errors import ProtocolError


EVENT_KINDS = {"intent", "progress", "decision", "correction", "asset", "guidance", "handoff", "state"}


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def request_hash(data: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def validate_event_envelope(event: dict[str, Any]) -> dict[str, Any]:
    required = ("event_id", "kind", "schema_version", "occurred_at", "source", "confirmation", "payload", "evidence")
    for field in required:
        if field not in event:
            raise ProtocolError("invalid_event_schema", f"missing event field: {field}")
    if event["kind"] not in EVENT_KINDS:
        raise ProtocolError("invalid_event_kind", f"invalid event kind: {event['kind']}")
    if not isinstance(event["evidence"], list):
        raise ProtocolError("invalid_event_schema", "evidence must be a list")
    return event
```

- [ ] **Step 6: Add request models**

Create `src/ai_workroot/protocol/model.py`:

```python
"""Protocol request and response models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_workroot.protocol.errors import ProtocolError
from ai_workroot.protocol.events import validate_event_envelope


PROTOCOL_VERSION = "workroot.v1"
SYNC_REASONS = {
    "startup",
    "continue",
    "before_work",
    "context_refresh",
    "after_error",
    "before_task_switch",
    "before_handoff",
    "manual_check",
    "before_high_risk_action",
}


def _require_protocol_version(data: dict[str, Any]) -> None:
    version = data.get("protocol_version")
    if not version:
        raise ProtocolError("missing_protocol_version")
    if version != PROTOCOL_VERSION:
        raise ProtocolError("unsupported_protocol_version")


@dataclass(frozen=True)
class SyncRequest:
    request_id: str
    agent: dict[str, Any]
    cwd: str | None
    workroot_id: str | None
    reason: str
    query: str
    known_state: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SyncRequest":
        _require_protocol_version(data)
        agent = data.get("agent") or {}
        if not data.get("request_id"):
            raise ProtocolError("missing_request_id")
        if not agent.get("name") or not agent.get("transport"):
            raise ProtocolError("invalid_agent")
        if not data.get("cwd") and not data.get("workroot_id"):
            raise ProtocolError("missing_workroot_locator")
        reason = data.get("reason")
        if reason not in SYNC_REASONS:
            raise ProtocolError("invalid_sync_reason")
        return cls(
            request_id=data["request_id"],
            agent=agent,
            cwd=data.get("cwd"),
            workroot_id=data.get("workroot_id"),
            reason=reason,
            query=data.get("query") or "",
            known_state=data.get("known_state") or {},
        )


@dataclass(frozen=True)
class CommitRequest:
    request_id: str
    exchange_lease_id: str
    idempotency_key: str
    atomic_batch: bool
    events: list[dict[str, Any]]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CommitRequest":
        _require_protocol_version(data)
        events = data.get("events")
        if not isinstance(events, list) or not events:
            raise ProtocolError("empty_event_batch")
        if data.get("atomic_batch") is False:
            raise ProtocolError("partial_batch_not_supported")
        for field in ("request_id", "exchange_lease_id", "idempotency_key"):
            if not data.get(field):
                raise ProtocolError(f"missing_{field}")
        return cls(
            request_id=data["request_id"],
            exchange_lease_id=data["exchange_lease_id"],
            idempotency_key=data["idempotency_key"],
            atomic_batch=True,
            events=[validate_event_envelope(event) for event in events],
        )
```

- [ ] **Step 7: Run model tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_models -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/ai_workroot/protocol tests/unit/test_protocol_models.py
git commit -m "feat: add workroot protocol request models"
```

### Task 3: SQLite Schema Upgrade

**Files:**
- Modify: `src/ai_workroot/state/sqlite.py`
- Create: `tests/unit/test_protocol_schema.py`

- [ ] **Step 1: Write schema tests**

Create `tests/unit/test_protocol_schema.py`:

```python
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.state.sqlite import initialize_workroot_sqlite


class ProtocolSchemaTest(unittest.TestCase):
    def open_db(self) -> sqlite3.Connection:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db_path = Path(tmp.name) / "workroot.sqlite"
        initialize_workroot_sqlite(db_path)
        return sqlite3.connect(db_path)

    def test_protocol_tables_exist(self) -> None:
        conn = self.open_db()
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual table')"
            ).fetchall()
        }
        self.assertIn("protocol_commit_batches", tables)
        self.assertIn("protocol_events", tables)
        self.assertIn("protocol_event_effects", tables)
        self.assertIn("exchange_leases", tables)
        self.assertIn("state_versions", tables)
        self.assertIn("task_runs", tables)
        self.assertIn("task_summaries", tables)

    def test_state_versions_are_workroot_scoped(self) -> None:
        conn = self.open_db()
        conn.execute(
            """
            INSERT INTO state_versions (workroot_id, scope, version, updated_at)
            VALUES ('wr_one', 'workroot', 1, '2026-05-26T10:00:00Z')
            """
        )
        conn.execute(
            """
            INSERT INTO state_versions (workroot_id, scope, version, updated_at)
            VALUES ('wr_two', 'workroot', 1, '2026-05-26T10:00:00Z')
            """
        )
        rows = conn.execute("SELECT COUNT(*) FROM state_versions WHERE scope = 'workroot'").fetchone()
        self.assertEqual(rows, (2,))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run schema tests to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_schema -v
```

Expected: FAIL because protocol tables are missing.

- [ ] **Step 3: Extend `REQUIRED_TABLES`**

In `src/ai_workroot/state/sqlite.py`, add:

```python
"protocol_commit_batches",
"protocol_events",
"protocol_event_effects",
"exchange_leases",
"state_versions",
"task_runs",
"task_summaries",
```

- [ ] **Step 4: Add protocol SQL schema**

Append the P0 protocol tables to `SCHEMA` in `src/ai_workroot/state/sqlite.py` using the exact SQL from the final Spec sections 13.1 through 13.8. Ensure `handoffs` and `tasks` upgrades are handled for existing DBs by adding missing columns through an upgrade helper.

Add helper:

```python
def add_column_if_missing(conn: sqlite3.Connection, table: str, column_name: str, definition: str) -> None:
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_name} {definition}")
```

Add after base schema creation:

```python
def upgrade_protocol_schema(conn: sqlite3.Connection) -> None:
    task_columns = {
        "role": "TEXT NOT NULL DEFAULT 'normal'",
        "parent_task_id": "TEXT NULL",
        "root_task_id": "TEXT NULL",
        "retention_policy": "TEXT NOT NULL DEFAULT 'until_closed'",
        "visibility": "TEXT NOT NULL DEFAULT 'normal'",
        "summary_id": "TEXT NULL",
        "rollup_summary_id": "TEXT NULL",
        "created_at": "TEXT NOT NULL DEFAULT '1970-01-01T00:00:00Z'",
        "updated_at": "TEXT NOT NULL DEFAULT '1970-01-01T00:00:00Z'",
        "closed_at": "TEXT NULL",
        "archived_at": "TEXT NULL",
        "metadata_json": "TEXT NOT NULL DEFAULT '{}'",
    }
    for column, definition in task_columns.items():
        add_column_if_missing(conn, "tasks", column, definition)
```

Call `upgrade_protocol_schema(conn)` from `initialize_workroot_sqlite()` after `conn.executescript(SCHEMA)`.

- [ ] **Step 5: Verify schema tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_schema -v
```

Expected: PASS.

- [ ] **Step 6: Verify existing work tests still pass**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_work_operations tests.unit.test_state -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/ai_workroot/state/sqlite.py tests/unit/test_protocol_schema.py
git commit -m "feat: add protocol sqlite schema"
```

### Task 4: Lease And State Versions

**Files:**
- Create: `src/ai_workroot/protocol/directives.py`
- Create: `src/ai_workroot/protocol/lease.py`
- Create: `tests/unit/test_protocol_lease.py`

- [ ] **Step 1: Write lease tests**

Create `tests/unit/test_protocol_lease.py` with tests for create, missing, expired, inactive, event not allowed, and state conflict.

Use this core assertion:

```python
self.assertEqual(result.error.code, "state_conflict")
self.assertEqual(result.directive["type"], "resync_required")
```

- [ ] **Step 2: Run lease tests to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_lease -v
```

Expected: FAIL because lease functions are missing.

- [ ] **Step 3: Implement directives**

Create `src/ai_workroot/protocol/directives.py`:

```python
"""Protocol directive builders."""

from __future__ import annotations


DIRECTIVE_TYPES = {
    "continue_task",
    "ask_user",
    "commit_required",
    "handoff_required",
    "resync_required",
    "promote_candidate",
    "archive_candidate",
    "blocked",
    "safe_to_stop",
    "no_persistent_work",
}


def directive(
    directive_type: str,
    *,
    goal: str | None = None,
    next_action: str | None = None,
    expected_events: list[str] | None = None,
    required_before_stop: list[str] | None = None,
    must_not: list[str] | None = None,
) -> dict[str, object]:
    if directive_type not in DIRECTIVE_TYPES:
        raise ValueError(f"unknown directive type: {directive_type}")
    return {
        "type": directive_type,
        "goal": goal,
        "next_action": next_action,
        "expected_events": expected_events or [],
        "required_before_stop": required_before_stop or [],
        "must_not": must_not or [],
        "ask_user_when": [],
        "metadata": {},
    }


def resync_required(next_action: str = "Call sync and retry if still relevant.") -> dict[str, object]:
    return directive("resync_required", next_action=next_action, expected_events=[])
```

- [ ] **Step 4: Implement lease functions**

Create `src/ai_workroot/protocol/lease.py` with:

```python
"""Exchange lease and state version helpers."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
import sqlite3

from ai_workroot.protocol.directives import resync_required


def now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass(frozen=True)
class LeaseValidationResult:
    ok: bool
    lease: dict[str, object] | None = None
    error: dict[str, object] | None = None
    directive: dict[str, object] | None = None


def load_state_versions(conn: sqlite3.Connection, workroot_id: str, scopes: list[str]) -> dict[str, int]:
    versions: dict[str, int] = {}
    for scope in scopes:
        row = conn.execute(
            "SELECT version FROM state_versions WHERE workroot_id = ? AND scope = ?",
            (workroot_id, scope),
        ).fetchone()
        versions[scope] = int(row[0]) if row else 0
    return versions


def bump_state_version(conn: sqlite3.Connection, workroot_id: str, scope: str) -> None:
    current = load_state_versions(conn, workroot_id, [scope])[scope]
    conn.execute(
        """
        INSERT INTO state_versions (workroot_id, scope, version, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(workroot_id, scope) DO UPDATE SET
          version=excluded.version,
          updated_at=excluded.updated_at
        """,
        (workroot_id, scope, current + 1, now_utc()),
    )
```

Continue in the same file with `create_lease()` and `validate_lease()` matching the final Spec.

- [ ] **Step 5: Run lease tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_lease -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ai_workroot/protocol/directives.py src/ai_workroot/protocol/lease.py tests/unit/test_protocol_lease.py
git commit -m "feat: add protocol lease validation"
```

### Task 5: Sync Controller Is Read-Only For Semantic Facts

**Files:**
- Create: `src/ai_workroot/protocol/controller.py`
- Create: `tests/unit/test_protocol_controller.py`

- [ ] **Step 1: Write sync tests**

Create tests that:

```python
def test_sync_returns_directive_lease_context_contract(self) -> None:
    ...

def test_sync_does_not_create_task_or_run(self) -> None:
    ...
```

The second test must count rows in `tasks`, `task_runs`, and `handoffs` before and after `sync`.

- [ ] **Step 2: Run sync tests to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_controller -v
```

Expected: FAIL because `controller.sync` is missing.

- [ ] **Step 3: Implement minimal `sync`**

In `src/ai_workroot/protocol/controller.py`, implement:

```python
def sync(request_data: dict[str, object]) -> dict[str, object]:
    request = SyncRequest.from_dict(request_data)
    workroot = resolve_workroot_for_protocol(request)
    conn = sqlite3.connect(workroot["sqlite_path"])
    directive_payload = choose_sync_directive(conn, workroot["workroot_id"], request)
    lease = create_lease(conn, workroot_id=workroot["workroot_id"], directive=directive_payload)
    return build_sync_response(workroot, directive_payload, lease, context={"brief": "", "refs": [], "warnings": []})
```

`resolve_workroot_for_protocol()` should reuse existing Workroot lookup behavior from command/status code and never write domain facts.

- [ ] **Step 4: Verify sync tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_controller -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ai_workroot/protocol/controller.py tests/unit/test_protocol_controller.py
git commit -m "feat: add read-only protocol sync"
```

### Task 6: Commit Batches, Event Ledger, And Idempotency

**Files:**
- Modify: `src/ai_workroot/protocol/controller.py`
- Create: `tests/unit/test_protocol_idempotency.py`

- [ ] **Step 1: Write idempotency tests**

Create tests for:

```text
same idempotency_key + same request_hash returns previous response
same idempotency_key + different request_hash returns idempotency_key_conflict
event ledger not double-applied
```

- [ ] **Step 2: Run idempotency tests to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_idempotency -v
```

Expected: FAIL because `commit` does not implement commit batches.

- [ ] **Step 3: Implement commit batch helpers**

In `src/ai_workroot/protocol/controller.py`, add:

```python
def load_existing_batch(conn: sqlite3.Connection, workroot_id: str, idempotency_key: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT request_hash, response_json, status
        FROM protocol_commit_batches
        WHERE workroot_id = ? AND idempotency_key = ?
        """,
        (workroot_id, idempotency_key),
    ).fetchone()
```

Add:

```python
def append_protocol_event(conn: sqlite3.Connection, *, batch_id: str, workroot_id: str, lease_id: str, request_id: str, idempotency_key: str, event: dict[str, object], received_at: str) -> None:
    conn.execute(
        """
        INSERT INTO protocol_events (
          event_id, batch_id, workroot_id, request_id, lease_id, idempotency_key,
          kind, schema_version, payload_json, evidence_json, confirmation_json,
          source_json, occurred_at, received_at, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event["event_id"],
            batch_id,
            workroot_id,
            request_id,
            lease_id,
            idempotency_key,
            event["kind"],
            event["schema_version"],
            canonical_json(event["payload"]),
            canonical_json({"items": event["evidence"]}),
            canonical_json(event["confirmation"]),
            canonical_json(event["source"]),
            event["occurred_at"],
            received_at,
            "accepted",
        ),
    )
```

- [ ] **Step 4: Implement `commit` idempotency shell**

Add `commit(request_data)` that:

```text
validates request
validates lease
computes request_hash
checks protocol_commit_batches
returns old response for same key/hash
returns idempotency_key_conflict for same key/different hash
opens one transaction
inserts protocol_commit_batches
appends protocol_events
applies projections
stores response_json
```

- [ ] **Step 5: Verify idempotency tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_idempotency -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ai_workroot/protocol/controller.py tests/unit/test_protocol_idempotency.py
git commit -m "feat: add protocol commit idempotency"
```

### Task 7: Minimal Projections

**Files:**
- Create: `src/ai_workroot/protocol/projections.py`
- Modify: `src/ai_workroot/protocol/controller.py`
- Create: `tests/unit/test_protocol_projections.py`

- [x] **Step 1: Write projection tests**

Create tests:

```text
test_commit_intent_creates_task_and_run
test_commit_progress_updates_run_and_returns_next_lease
test_commit_handoff_returns_safe_to_stop
test_state_transition_updates_task_status
```

- [x] **Step 2: Run projection tests to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_projections -v
```

Expected: FAIL because projections are missing.

- [x] **Step 3: Implement projection dispatcher**

Create `src/ai_workroot/protocol/projections.py`:

```python
"""P0 protocol event projections."""

from __future__ import annotations

import sqlite3
import uuid

from ai_workroot.protocol.lease import bump_state_version, now_utc


def apply_projection(conn: sqlite3.Connection, *, workroot_id: str, lease: dict[str, object], event: dict[str, object]) -> list[dict[str, str]]:
    kind = event["kind"]
    if kind == "intent":
        return project_intent(conn, workroot_id=workroot_id, event=event)
    if kind == "progress":
        return project_progress(conn, workroot_id=workroot_id, event=event)
    if kind == "handoff":
        return project_handoff(conn, workroot_id=workroot_id, event=event)
    if kind == "state":
        return project_state(conn, workroot_id=workroot_id, event=event)
    raise ValueError(f"projection not implemented for event kind: {kind}")
```

Implement `project_intent`, `project_progress`, `project_handoff`, and `project_state` with direct SQL inside the controller transaction. Do not call existing helpers that commit internally.

- [x] **Step 4: Wire projections into commit**

In `controller.commit`, call:

```python
effects = apply_projection(conn, workroot_id=lease_workroot_id, lease=lease_dict, event=event)
```

Then write each effect into `protocol_event_effects`.

- [x] **Step 5: Verify projection tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_projections -v
```

Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add src/ai_workroot/protocol/projections.py src/ai_workroot/protocol/controller.py tests/unit/test_protocol_projections.py
git commit -m "feat: add protocol p0 projections"
```

### Task 8: Continuity Context And Next Agent Resume

**Files:**
- Create: `src/ai_workroot/context/continuity.py`
- Modify: `src/ai_workroot/protocol/controller.py`
- Create: `tests/integration/test_agent_protocol_loop.py`

- [ ] **Step 1: Write integration loop test**

Create `tests/integration/test_agent_protocol_loop.py` with one end-to-end loop:

```text
sync before_work returns commit_required
commit intent creates task/run
commit progress updates run
commit handoff stores current handoff
new sync continue includes latest handoff
```

- [ ] **Step 2: Run integration test to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.integration.test_agent_protocol_loop -v
```

Expected: FAIL until context continuity is wired.

- [ ] **Step 3: Implement continuity loader**

Create `src/ai_workroot/context/continuity.py`:

```python
"""Minimal task continuity package for protocol sync."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class ContinuityPackage:
    brief: str
    refs: list[dict[str, str]]
    warnings: list[str]

    def to_dict(self) -> dict[str, object]:
        return {"brief": self.brief, "refs": self.refs, "warnings": self.warnings}


def load_continuity_package(conn: sqlite3.Connection, *, workroot_id: str, task_id: str | None) -> ContinuityPackage:
    if not task_id:
        return ContinuityPackage(brief="", refs=[], warnings=[])
    summary = conn.execute(
        """
        SELECT summary_id, summary_text, status
        FROM task_summaries
        WHERE workroot_id = ? AND task_id = ?
        ORDER BY generated_at DESC
        LIMIT 1
        """,
        (workroot_id, task_id),
    ).fetchone()
    handoff = conn.execute(
        """
        SELECT handoff_id, current_state, next_action
        FROM handoffs
        WHERE workroot_id = ? AND task_id = ? AND status = 'current'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (workroot_id, task_id),
    ).fetchone()
    refs: list[dict[str, str]] = []
    brief = ""
    if summary:
        brief = summary[1]
        refs.append({"type": "task_summary", "id": summary[0], "role": "primary", "summary": summary[1]})
    if handoff:
        refs.append({"type": "handoff", "id": handoff[0], "role": "next_step", "summary": handoff[2] or handoff[1]})
    return ContinuityPackage(brief=brief, refs=refs, warnings=[])
```

- [ ] **Step 4: Use continuity loader from sync**

In `controller.sync`, replace minimal context for existing task with:

```python
context = load_continuity_package(conn, workroot_id=workroot_id, task_id=task_id).to_dict()
```

- [ ] **Step 5: Verify integration loop**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.integration.test_agent_protocol_loop -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ai_workroot/context/continuity.py src/ai_workroot/protocol/controller.py tests/integration/test_agent_protocol_loop.py
git commit -m "feat: add protocol continuity loop"
```

### Task 9: CLI Adapter

**Files:**
- Create: `src/ai_workroot/commands/agent_exchange.py`
- Modify: `src/ai_workroot/cli/main.py`
- Create: `tests/unit/test_agent_exchange_command.py`
- Modify: `tests/smoke/test_cli_discovery.py`

- [ ] **Step 1: Write command tests**

Create tests that patch `protocol.controller.sync` and `protocol.controller.commit` and assert `commands.agent_exchange` delegates.

- [ ] **Step 2: Run command tests to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_agent_exchange_command -v
```

Expected: FAIL because command adapter is missing.

- [ ] **Step 3: Implement command adapter**

Create `src/ai_workroot/commands/agent_exchange.py`:

```python
"""Agent protocol command adapter."""

from __future__ import annotations

import json
from pathlib import Path

from ai_workroot.protocol.controller import commit, sync


def run_exchange_request(request_path: Path) -> dict[str, object]:
    envelope = json.loads(request_path.read_text(encoding="utf-8"))
    action = envelope.get("action")
    request = envelope.get("request") or {}
    if action == "sync":
        return sync(request)
    if action == "commit":
        return commit(request)
    return {
        "ok": False,
        "error": {"code": "invalid_exchange_action", "message": "Invalid exchange action.", "details": {}},
        "directive": {"type": "resync_required", "goal": None, "next_action": "Use sync or commit.", "expected_events": [], "required_before_stop": [], "must_not": []},
    }
```

- [ ] **Step 4: Add CLI subcommands**

Modify `src/ai_workroot/cli/main.py`:

```text
Add primary command: agent
Subcommands:
  exchange --request
  sync --cwd --agent --query
  commit --request
```

Keep CLI as adapter-only.

- [ ] **Step 5: Verify command and discovery tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_agent_exchange_command tests.smoke.test_cli_discovery -v
PYTHONPATH=src python3 -m ai_workroot --help
```

Expected: PASS and help includes `agent`.

- [ ] **Step 6: Commit**

```bash
git add src/ai_workroot/commands/agent_exchange.py src/ai_workroot/cli/main.py tests/unit/test_agent_exchange_command.py tests/smoke/test_cli_discovery.py
git commit -m "feat: add agent protocol cli adapter"
```

### Task 10: Import Boundaries And Quality Gate

**Files:**
- Modify: `tests/unit/test_import_boundaries.py`

- [ ] **Step 1: Add import boundary assertions**

Add tests:

```text
work/* must not import ai_workroot.protocol
assets/* must not import ai_workroot.protocol
handoff/* must not import ai_workroot.protocol
protocol/* must not import ai_workroot.cli
commands/agent_exchange.py must not import sqlite3
```

- [ ] **Step 2: Run boundary tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_import_boundaries -v
```

Expected: PASS.

- [ ] **Step 3: Run focused P0 test suite**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.unit.test_protocol_models \
  tests.unit.test_protocol_schema \
  tests.unit.test_protocol_lease \
  tests.unit.test_protocol_idempotency \
  tests.unit.test_protocol_controller \
  tests.unit.test_protocol_projections \
  tests.unit.test_agent_exchange_command \
  tests.integration.test_agent_protocol_loop \
  tests.unit.test_import_boundaries \
  tests.smoke.test_cli_discovery \
  tests.smoke.test_package_entrypoint
```

Expected: PASS.

- [ ] **Step 4: Run package quality gate**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover tests/unit tests/integration tests/smoke
PYTHONPATH=src python3 -m ai_workroot --version
PYTHONPATH=src python3 -m ai_workroot doctor --cwd .
```

Expected: tests pass, version is `AI Workroot 0.9.531`, doctor remains PASS or reports only pre-existing non-P0 issues.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_import_boundaries.py
git commit -m "test: enforce protocol import boundaries"
```

## Self-Review Checklist

- [ ] P0 does not implement per-turn persistence.
- [ ] `sync` creates no Task, TaskRun, Inbox, Handoff, or Asset semantic facts.
- [ ] Task creation happens through `commit(event=intent)`.
- [ ] SQLite remains under `cache/workroot.sqlite`.
- [ ] Runtime views remain under `runtime/`.
- [ ] Commit idempotency is batch-scoped through `protocol_commit_batches`.
- [ ] Same key and same request hash returns prior response.
- [ ] Same key and different request hash returns `idempotency_key_conflict`.
- [ ] CLI is adapter-only.
- [ ] Domain packages do not import `protocol`.
