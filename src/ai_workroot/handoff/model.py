"""Handoff package models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HandoffPackage:
    handoff_id: str
    workroot_id: str
    title: str
    target: str = "generic"
    body: str = ""
