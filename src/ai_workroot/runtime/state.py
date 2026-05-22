"""Retired compatibility state entry points.

Active Clean Workroot initialization lives in ``runtime.environment`` and
``runtime.init``. This module remains only to fail old imports explicitly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class RetiredStateRuntimeError(RuntimeError):
    """Raised when retired compatibility state APIs are called."""


def initialize_ai_workroot_home(*_args: Any, **_kwargs: Any) -> None:
    raise RetiredStateRuntimeError("runtime.state compatibility initialization is retired; use runtime.environment")


def initialize_workroot_state(*_args: Any, **_kwargs: Any) -> None:
    raise RetiredStateRuntimeError("runtime.state compatibility initialization is retired; use runtime.init")


def read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    import json

    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
