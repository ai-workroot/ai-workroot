"""Core Asset model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AssetSurface:
    surface_id: str
    workroot_id: str
    path: str
    surface_type: str
    allowed_asset_types: tuple[str, ...]
    git_policy: str
    created_by: str
    is_local_only: bool = False
    created_at: str | None = None

    def allows(self, asset_type: str) -> bool:
        return asset_type in self.allowed_asset_types


@dataclass(frozen=True)
class AssetPublication:
    publication_id: str
    asset_id: str
    workroot_id: str
    surface_id: str
    target_path: str
    publication_status: str
    published_by: str
    published_at: str | None = None
    source_task_id: str | None = None
    reason: str | None = None
    git_policy: str | None = None


@dataclass
class Asset:
    asset_id: str
    workroot_id: str
    asset_type: str
    title: str
    summary: str = ""
    lifecycle_status: str = "active"
    publication_status: str = "internal"
    surface_id: str | None = None
    current_path: str | None = None
    original_path: str | None = None
    content_hash: str | None = None
    size_bytes: int | None = None
    modified_at: str | None = None
    last_seen_at: str | None = None
    missing_since: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def publish(self, surface: AssetSurface, target_path: str, published_by: str) -> AssetPublication:
        if not surface.allows(self.asset_type):
            raise ValueError(f"surface {surface.surface_id!r} does not allow asset type {self.asset_type!r}")

        self.publication_status = "published"
        self.surface_id = surface.surface_id
        self.current_path = target_path
        if self.original_path is None:
            self.original_path = target_path

        return AssetPublication(
            publication_id=f"pub_{self.asset_id}",
            asset_id=self.asset_id,
            workroot_id=self.workroot_id,
            surface_id=surface.surface_id,
            target_path=target_path,
            publication_status="published",
            published_by=published_by,
            git_policy=surface.git_policy,
        )

    def mark_missing(self, missing_since: str) -> None:
        self.lifecycle_status = "missing"
        self.missing_since = missing_since

    def update_fingerprint(self, content_hash: str, size_bytes: int, modified_at: str) -> None:
        self.content_hash = content_hash
        self.size_bytes = size_bytes
        self.modified_at = modified_at
        self.last_seen_at = modified_at
