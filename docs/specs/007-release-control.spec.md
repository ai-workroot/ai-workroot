# Spec 007 — Release Control

Status: accepted  
Target: 0.9.530

## Purpose

Define release, quiet, archive, tombstone, redaction, and deletion control over recallable objects.

## Entities

### ReleaseRecord

General release overlay record.

Fields:

```text
release_id
workroot_id
target_ref
release_level
recall_rule
reason
created_at
created_by
policy_ref
```

### ReleaseTargetRef

References a recallable object without coupling to its schema.

Fields:

```text
target_type
target_id
workroot_id
target_title
target_summary
```

Allowed target types:

```text
asset
task
work_action
agent_run
checkpoint
handoff
context_package
context_trace
retrieval_card
relationship_edge
```

### ReleaseLevel

```text
quiet
archived
tombstone
redacted
deleted
```

### Tombstone

Entity name is `Tombstone`. Do not use `TombstoneMarker`.

Fields:

```text
tombstone_id
workroot_id
target_ref
title
symbolic_note
lesson_asset_id
memorial_date
recall_rule
visibility_policy
created_at
created_by
```

Tombstone means intentional remembrance. It is visible and explicitly reviewable.

### Redaction

Fields:

```text
redaction_id
workroot_id
target_ref
redacted_fields
redaction_reason
created_at
created_by
```

### DeletionRecord

Fields:

```text
deletion_id
workroot_id
target_ref
minimum_audit_note
created_at
created_by
```

DeletionRecord must not preserve deleted sensitive details.

## Default behavior in 0.9.530

- `quiet`: annotate/deprioritize, no hard exclusion.
- `archived`: annotate/lower default recall, no hard exclusion.
- `tombstone`: model, annotate, trace, visible, explicit review allowed; no hard ordinary-context exclusion yet.
- `redacted`: strict protection.
- `deleted`: strict protection.
- safety-sensitive: strict protection according to safety policy.

## Propagation

Release Control emits `ReleasePropagationEvent` to update:

- indexes;
- context candidates;
- FTS entries;
- relationship traversal projections;
- context selection traces;
- doctor checks.

## Negative rules

- Do not mutate `Task.status` to `tombstone`.
- Do not mutate `WorkAction.status` to `tombstone`.
- Do not convert deletion to Tombstone without user choice.
- Do not hide deleted/redacted details in derived indexes.

## Acceptance

- Tombstone entity exists with correct name.
- ReleaseRecord can cover Task without modifying Task.
- Redaction/deletion is enforced in ordinary context and indexes.
- Tombstone is visible and traceable, but not forcibly excluded in 0.9.530.
- ContextTrace records release state when relevant.
