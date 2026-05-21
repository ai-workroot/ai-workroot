# Spec 010 — Context Control

Status: accepted
Target: 0.9.530

## Purpose

Generate agent-ready context through explicit control of recall, safety, relevance, budget, and traceability.

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
- Graph business wording replaced with Relationship Network in output/docs where appropriate.
