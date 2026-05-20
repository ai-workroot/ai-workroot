# Lifecycle Policy

AI Workroot should not treat every old file as equally current forever.

Durable knowledge, decisions, artifacts, and tasks should carry enough lifecycle information for future agents to retrieve the right context without reviving obsolete or painful material by accident.

## Status

Recommended status values:

- `draft`: not yet stable
- `active`: current and usable
- `tentative`: useful but uncertain
- `superseded`: replaced by a newer entry
- `obsolete`: preserved for traceability, not reuse
- `invalidated`: proven wrong or unsafe to reuse
- `released`: removed from normal recall by user choice
- `deleted`: removed by explicit user choice

## Temperature

Temperature controls retrieval:

- `hot`: active work or current operating context
- `warm`: useful when relevant
- `cold`: preserved history, not default recall
- `archived`: explicit review only
- `released`: excluded from normal retrieval
- `tombstone`: intentional remembrance only
- `deleted`: not retrievable

## Confidence

Recommended confidence values:

- `high`
- `medium`
- `low`
- `unknown`

Agents should avoid presenting low-confidence or stale entries as current truth.

## Replacement

When an entry is superseded, obsolete, or invalidated, link it to the replacement through:

- `superseded_by`
- `link_registry.csv`
- the entry's own "Replacement" or "Later Validation" section

Do not silently overwrite history when traceability matters.

## Review

Use `review_after` when knowledge may decay or require future verification.

Temporal values should follow `.workroot/kernel/config/time.md`.

Examples:

- tool-specific knowledge
- legal, medical, tax, or policy context
- model or platform behavior
- team process rules
- personal preferences that may change

## Default Rule

New durable entries should start as:

- status: `active` or `draft`
- temperature: `warm`
- confidence: `unknown` unless evidence supports a stronger value

Active tasks should start as `hot`.
