"""Filesystem contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class FileInfo:
    path: str
    size_bytes: int
    modified_at: str


@runtime_checkable
class FileSystem(Protocol):
    def read_text(self, path: str) -> str:
        """Read UTF-8 text from a path."""

    def write_text(self, path: str, text: str) -> None:
        """Write UTF-8 text to a path."""

    def stat(self, path: str) -> FileInfo:
        """Return file metadata."""
