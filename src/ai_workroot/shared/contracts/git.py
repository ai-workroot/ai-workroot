"""Git contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class GitStatus:
    branch: str
    is_dirty: bool
    head: str


@runtime_checkable
class GitStatusProvider(Protocol):
    def status(self, cwd: str) -> GitStatus:
        """Return git status for a working directory."""
