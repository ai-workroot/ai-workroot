# Forgetting And Release

AI Workroot is designed to remember, but a healthy mind also needs to release.

People make mistakes, experience pain, and pass through difficult periods. After the lesson has been extracted, not every painful detail should remain in active context forever.

Release is not denial, irresponsibility, or pretending the past never happened. It is a user-directed way to preserve growth while reducing unnecessary reactivation of pain.

The default philosophy is:

> Preserve the lesson. Release the unnecessary pain. Live in the present. Move toward the future.

## User Choice

Forgetting is a user-controlled act.

The Workroot must not force a universal value judgment about what should be forgotten. Some people may want to preserve painful memories as part of their history. Others may want to release them after the lesson is learned. Some may want to keep only a small tombstone for remembrance, mourning, or ritual closure.

Both choices are valid.

## Release Workflow

When the user chooses to release something:

1. Extract the useful lesson first, if one exists.
2. Preserve that lesson in `space/mind/knowledge/`, `space/mind/principles/`, `space/mind/decisions/`, or `space/mind/patterns/`.
3. Choose the release level.
4. Move or summarize the released context under `space/mind/released/`, unless the user chooses deletion.
5. Update `.workroot/runtime/index/mind_registry.csv` with the release or tombstone entry when useful.
6. Add relationship links when useful, especially from the preserved lesson to the released context.
7. Exclude released context from normal startup and default retrieval.

## Release Levels

- `active`: normal memory or knowledge; agents may use it when relevant.
- `quiet`: preserved but not used by default.
- `archived`: retained for explicit review only.
- `tombstone`: a minimal memorial marker; the raw pain is not kept active.
- `redacted`: details removed; lesson retained.
- `deleted`: removed by explicit user choice.

## Tombstones

A tombstone is a quiet corner for the past.

It can be used to remember that something mattered, to honor a loss, to mark an old mistake, or to close a difficult period without carrying the full raw context forward.

In AI Workroot, `tombstone` is a first-class kernel concept. It must not be renamed away or collapsed into a generic archive. The word matters because it preserves the intended human meaning: remembrance without reactivation.

A tombstone should usually contain only:

- a short title
- a symbolic note
- the lesson or growth that remains
- optional dates or source links
- a retrieval rule

It should not become a hidden archive of painful detail.

Tombstones are optional. The user may keep them, visit them intentionally, redact them further, or delete them completely.

In v0.9.527, tombstone support is intentionally a concept, interface, registry, and retrieval boundary. It is not yet a deep product workflow.

Future versions may evolve tombstones through deeper philosophical, engineering, and product design. That evolution should remain backward-compatible with v0.9.527 tombstone markers and should not force every Workroot to adopt one universal ritual or emotional model.

Tombstone entries should use:

- `type=tombstone`
- `temperature=tombstone`
- `release_level=tombstone`
- a clear `retrieval_rule`

## Default Policy

Default to `quiet` when the user says they want to forget or move on but has not explicitly requested deletion.

Deletion must be explicit.

For `deleted`, either remove the registry row entirely or keep only a minimal deletion marker with no painful detail. A deleted entry should not become a hidden archive or a tombstone unless the user explicitly chooses `tombstone`.

## Agent Behavior

Agents should:

- help extract the lesson before release
- move released items to `space/mind/released/`
- update indexes and relationships
- avoid resurfacing released material in normal work
- ask before using painful or released context
- respect the user's current intention and future-facing direction

Agents should not:

- repeatedly surface painful memories because they are technically relevant
- treat every past mistake as active identity
- delete material without explicit user instruction
- hide safety-critical, legal, or integrity-relevant context without user awareness

## Deletion

If the user explicitly chooses deletion, remove the relevant files and update registries.

If the item has already produced reusable knowledge, preserve the knowledge entry when appropriate and remove only the painful or unnecessary source detail.
