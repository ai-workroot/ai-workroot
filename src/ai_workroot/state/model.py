"""Core WorkrootEnvironment model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkrootEnvironment:
    home: str
    version: str = "0.9.530"
