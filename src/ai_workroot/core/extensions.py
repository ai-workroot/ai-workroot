"""Core extension boundary model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Capability:
    capability_id: str
    name: str
    status: str = "reserved"

