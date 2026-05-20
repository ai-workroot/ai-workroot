# Spec 006 — Asset Model

Status: accepted
Target: 0.9.530

## Purpose

Unify user value objects under Asset and define publication/staging/path tracking.

## Asset definition

Asset is a user value object. It may be internal, staged, or published.

Asset subtypes include:

```text
source
generated
knowledge
decision
result
reference
handoff
architecture_doc
spec
adr
release_note
review_report
code
test
template
history_note
dev_note
```

`Knowledge`, `Decision`, and `Result` are not top-level domains.

## Asset fields

Minimum fields:

```text
asset_id
workroot_id
asset_type
title
summary
lifecycle_status
publication_status
surface_id
current_path
original_path
content_hash
size_bytes
modified_at
last_seen_at
missing_since
created_at
updated_at
```

## Lifecycle statuses

```text
draft
active
quiet
archived
superseded
tombstoned
released
missing
```

Note: tombstoned lifecycle state must be coordinated with Release Control `Tombstone`.

## Publication status

```text
internal
staged
published
unpublished
```

## AssetSurface

Represents allowed output surface.

Fields:

```text
surface_id
workroot_id
path
surface_type
allowed_asset_types
git_policy
is_local_only
created_by
created_at
```

## AssetPublication

Records a publication event.

Fields:

```text
publication_id
asset_id
workroot_id
surface_id
target_path
publication_status
published_at
published_by
source_task_id
reason
git_policy
```

## Publication policy

Modes:

```text
project-native
existing-surfaces-only
workroot-managed-asset-folder
internal-drafts-only
```

bootstrap-dev uses `project-native`.

## Path history

Must anticipate:

- file renamed;
- file moved;
- file deleted;
- file modified;
- same hash at new path;
- same path with new hash;
- missing path;
- ambiguous duplicates.

Do not fully implement advanced resolver if too large, but schema/model must preserve fields.

## User directory write rules

Only Published Assets write to user directory.

ContextPackage, ContextTrace, Candidate, FTS row, logs, and debug output are not user assets.

## Acceptance

- `knowledge_items` no longer represents top-level Knowledge domain.
- Decision/Knowledge/Result map to Asset type.
- Asset publication has explicit policy/surface.
- bootstrap-dev maps formal assets to project-native directories.
- no unstructured auto-generated junk is written to user root.
