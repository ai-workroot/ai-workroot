# ADR-0002 — Lightweight Core/Runtime Architecture

Status: accepted

## Decision

Use DDD only for strategic modeling. Implement with `core / contracts / runtime / storage / indexing / agent / cli`.

## Rationale

Pure DDD directories are too heavy for an early open-source project. The chosen structure preserves domain clarity while keeping contributors oriented by practical modules.

## Consequences

- Core holds domain concepts.
- Contracts holds protocols.
- Runtime orchestrates.
- Storage/indexing/agent implement capabilities.
- CLI stays thin.
