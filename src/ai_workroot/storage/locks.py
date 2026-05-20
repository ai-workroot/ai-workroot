"""File locking helpers."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import time

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback.
    fcntl = None  # type: ignore[assignment]


@contextmanager
def file_lock(path: Path, timeout: float = 10.0):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    deadline = time.monotonic() + timeout

    if fcntl is None:
        sentinel_path = path.with_suffix(path.suffix + ".sentinel")
        while True:
            try:
                sentinel = sentinel_path.open("x", encoding="utf-8")
                break
            except FileExistsError as exc:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"timed out waiting for lock: {path}") from exc
                time.sleep(0.05)
        try:
            with sentinel:
                sentinel.write(str(time.time()))
            yield path
        finally:
            sentinel_path.unlink(missing_ok=True)
        return

    with path.open("a+", encoding="utf-8") as lock_file:
        while True:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError as exc:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"timed out waiting for lock: {path}") from exc
                time.sleep(0.05)
        try:
            yield path
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
