"""Ordered migration runner for AI Workroot managed state."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import json
import os
from pathlib import Path
import time


MigrationAction = Callable[[Path], None]


@dataclass(frozen=True)
class Migration:
    migration_id: str
    scope: str
    apply_fn: MigrationAction


def now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def read_migration_records(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    records: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def append_migration_record(path: Path, record: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


@contextmanager
def migration_lock(root: Path, scope: str, timeout: float = 10.0) -> Iterator[None]:
    lock_dir = root / "migrations/locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / f"{scope}.lock"
    start = time.monotonic()
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"pid={os.getpid()}\ncreated_at={now_utc()}\n".encode("utf-8"))
            os.close(fd)
            break
        except FileExistsError as exc:
            if time.monotonic() - start > timeout:
                raise TimeoutError(f"timed out waiting for migration lock: {lock_path}") from exc
            time.sleep(0.02)
    try:
        yield
    finally:
        lock_path.unlink(missing_ok=True)


class MigrationRunner:
    def __init__(self, root: Path, migrations: list[Migration]) -> None:
        self.root = root
        self.migrations = sorted(migrations, key=lambda item: item.migration_id)

    def record_path(self, scope: str) -> Path:
        return self.root / f"migrations/{scope}.jsonl"

    def applied_ids(self, scope: str) -> set[str]:
        return {
            record["migrationId"]
            for record in read_migration_records(self.record_path(scope))
            if record.get("status") == "applied"
        }

    def apply(self, scope: str) -> None:
        with migration_lock(self.root, scope):
            applied = self.applied_ids(scope)
            for migration in self.migrations:
                if migration.scope != scope or migration.migration_id in applied:
                    continue
                started_at = now_utc()
                try:
                    migration.apply_fn(self.root)
                except Exception as exc:
                    append_migration_record(
                        self.record_path(scope),
                        {
                            "migrationId": migration.migration_id,
                            "scope": scope,
                            "status": "failed",
                            "startedAt": started_at,
                            "completedAt": now_utc(),
                            "checksum": "",
                            "error": str(exc),
                        },
                    )
                    raise SystemExit(f"migration failed: {migration.migration_id}: {exc}") from exc
                append_migration_record(
                    self.record_path(scope),
                    {
                        "migrationId": migration.migration_id,
                        "scope": scope,
                        "status": "applied",
                        "startedAt": started_at,
                        "completedAt": now_utc(),
                        "checksum": "",
                        "error": "",
                    },
                )
                applied.add(migration.migration_id)
