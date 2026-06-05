"""Core Relationship Network model."""

from __future__ import annotations

from dataclasses import dataclass, field


RELATIONSHIP_TYPES = {
    "uses",
    "produces",
    "updates",
    "supersedes",
    "supports",
    "contradicts",
    "references",
    "belongs_to",
    "related_to",
    "derived_from",
    "handoff_to",
    "used_in_context",
    "decomposes_to",
    "covered_by_release",
}


@dataclass(frozen=True)
class SourceRef:
    source_type: str
    source_id: str


@dataclass(frozen=True)
class RelationshipNode:
    node_id: str
    workroot_id: str
    node_type: str
    title: str = ""
    target_type: str = ""
    target_id: str = ""


@dataclass(frozen=True)
class RelationshipEvidence:
    evidence_id: str
    edge_id: str
    evidence_type: str
    source_ref: SourceRef
    asset_id: str | None = None
    task_id: str | None = None
    context_trace_id: str | None = None
    snippet_hash: str | None = None
    note: str | None = None
    created_at: str | None = None


@dataclass(frozen=True)
class RelationshipSignal:
    edge_id: str
    from_node_id: str
    to_node_id: str
    relationship_type: str
    confidence: float
    reason: str = "relationship-edge"
    matched_source_refs: tuple[SourceRef, ...] = ()


@dataclass
class RelationshipEdge:
    edge_id: str
    workroot_id: str
    from_node_id: str
    to_node_id: str
    relationship_type: str
    created_by: str
    confidence: float = 1.0
    status: str = "active"
    created_at: str | None = None
    updated_at: str | None = None
    evidence: tuple[RelationshipEvidence, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.relationship_type not in RELATIONSHIP_TYPES:
            raise ValueError(f"unsupported relationship type: {self.relationship_type!r}")

    def attach_evidence(self, evidence: RelationshipEvidence) -> None:
        if evidence.edge_id != self.edge_id:
            raise ValueError("relationship evidence edge_id does not match edge")
        self.evidence = (*self.evidence, evidence)
