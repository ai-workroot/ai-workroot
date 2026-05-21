# ADR-0004 — Release Control and Tombstone

Status: accepted

## Decision

Release Control is a core domain. Tombstone is a first-class entity named `Tombstone`, not `TombstoneMarker`.

## Rationale

Release, tombstone, redaction, and deletion can apply to any recallable object without mutating the target object's factual identity. Tombstone is a human-centered memorial concept, not a technical marker.

## Consequences

- Release Control overlays targets through `ReleaseTargetRef`.
- Tombstone/quiet/archive are modeled and traceable in 0.9.530.
- Redaction/deletion/safety-sensitive content is protected immediately.
