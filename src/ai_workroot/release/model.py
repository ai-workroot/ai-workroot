"""Core Release Control model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReleaseTargetRef:
    target_type: str
    target_id: str
    workroot_id: str
    target_title: str | None = None
    target_summary: str | None = None


@dataclass(frozen=True)
class ReleaseRecord:
    release_id: str
    workroot_id: str
    target_ref: ReleaseTargetRef
    release_level: str
    recall_rule: str = "default"
    reason: str | None = None
    created_at: str | None = None
    created_by: str | None = None
    policy_ref: str | None = None

    def strictly_protects_content(self) -> bool:
        return self.release_level in {"redacted", "deleted"}


@dataclass(frozen=True)
class Tombstone:
    tombstone_id: str
    workroot_id: str
    target_ref: ReleaseTargetRef
    title: str
    symbolic_note: str
    lesson_asset_id: str | None = None
    memorial_date: str | None = None
    recall_rule: str = "explicit_review"
    visibility_policy: str = "visible"
    created_at: str | None = None
    created_by: str | None = None

    def allows_explicit_review(self) -> bool:
        return self.recall_rule != "never"

    def strictly_protects_content(self) -> bool:
        return False


@dataclass(frozen=True)
class Redaction:
    redaction_id: str
    workroot_id: str
    target_ref: ReleaseTargetRef
    redacted_fields: tuple[str, ...]
    redaction_reason: str
    created_at: str | None = None
    created_by: str | None = None

    def strictly_protects_content(self) -> bool:
        return True


@dataclass(frozen=True)
class DeletionRecord:
    deletion_id: str
    workroot_id: str
    target_ref: ReleaseTargetRef
    minimum_audit_note: str
    created_at: str | None = None
    created_by: str | None = None

    def strictly_protects_content(self) -> bool:
        return True


@dataclass(frozen=True)
class ReleasePropagationEvent:
    event_id: str
    release_id: str
    target_ref: ReleaseTargetRef
    event_type: str
