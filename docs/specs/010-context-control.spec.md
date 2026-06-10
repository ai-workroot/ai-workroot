# Spec 010 — Context Control

Status: accepted; amended by Spec 042
Target: 0.9.530 base, 0.9.531+ strategy amendment

## Purpose

Generate agent-ready context through explicit control of recall, safety, relevance, budget, and traceability.

For the current WorkSignal-first, lease-aware, layered strategy contract, see
`042-agent-protocol-context-strategy.spec.md`.

## Inputs

- WorkrootEnvironment / WorkrootRegistration
- WorkrootCharter
- active Task / Task hierarchy summary
- Assets
- Release Control records
- Relationship Network projections
- Retrieval results
- ContextRecallHints / Context Cards
- Context mode
- Agent type
- Query
- Token/latency budget

## Outputs

- ContextPackage
- ContextTrace
- selected/dropped candidate records
- budget trim decisions
- usage events

## ContextController responsibilities

- resolve Workroot;
- load Charter and active Task;
- consume protocol focus, WorkSignal, known refs, and internal lease strategy signals;
- compile a recall/disclosure plan before detailed retrieval;
- request retrieval;
- read release state;
- read relationship signals;
- materialize active ContextRecallHints into candidate read models;
- filter safety and lifecycle;
- score candidates;
- trim by budget;
- render context package;
- write trace;
- emit usage events.

## Non-responsibilities

Context Control must not:

- publish assets;
- write user directory;
- maintain Relationship canonical truth;
- build indexes;
- run migrations;
- repair system state;
- create Native Agent Entry.

## Modes

```text
fast
standard
quality
deep
```

Rules:

- `deep` requires explicit request.
- `quality` must be traceable; if only budget expansion in current version, trace must say so.
- No remote LLM, remote embedding, or vector DB hot path in 0.9.530.

## Budget

Use conservative token estimate. Do not rely only on whitespace split.

Must support:

- target tokens;
- hard token limit;
- agent budget;
- final fallback if trim sections cannot satisfy limit.

## Release behavior

- tombstone/quiet/archive: trace and annotate, no hard default exclusion in 0.9.530.
- redacted/deleted/safety-sensitive: must not enter ordinary ContextPackage.

## Acceptance

- ContextPackage not written to user directory.
- ContextTrace not written to user directory.
- ContextTrace includes selected/dropped reasons.
- Redacted/deleted content excluded.
- Hard token limit respected using conservative estimate/fallback.
- Deep evidence retrieval is scoped and plan-constrained.
- Internal disclosure layer names and lease internals are not ordinary user-facing context.
- Graph business wording replaced with Relationship Network in output/docs where appropriate.
