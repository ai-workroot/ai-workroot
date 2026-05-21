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
