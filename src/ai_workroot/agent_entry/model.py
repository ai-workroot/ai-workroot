"""Core Agent Interface model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionHint:
    permission: str
    reason: str
