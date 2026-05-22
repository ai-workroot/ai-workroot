"""Core Retrieval and Index Control model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IndexManifest:
    index_id: str
    index_kind: str
    source_high_watermark: str
    built_high_watermark: str | None = None
    status: str = "ready"

    def is_stale(self) -> bool:
        return self.built_high_watermark != self.source_high_watermark

    def mark_built(self, high_watermark: str) -> None:
        self.built_high_watermark = high_watermark
        self.status = "ready"


@dataclass(frozen=True)
class ContextRecallHint:
    """Core retrieval anchor for the product-facing Context Card concept."""

    hint_id: str
    workroot_id: str
    target_type: str
    target_id: str
    title: str
    summary: str = ""
    scope_type: str = ""
    scope_id: str = ""
    kind: str = "context-card"
    priority: str = "normal"
    recall_rule: str = "task-related"
    lifecycle_status: str = "active"
    origin: str = "manual"
    source_ref: str = ""
    created_at: str = ""
    updated_at: str = ""
