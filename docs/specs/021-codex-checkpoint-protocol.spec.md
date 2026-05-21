# Spec 021 — Codex Checkpoint Protocol

Status: accepted
Applies to: 0.9.530

## Purpose

Codex must work in checkpoints because this release touches many files.

## Checkpoint rules

After each implementation phase, Codex must report:

1. Files changed.
2. Capabilities preserved.
3. Tests run.
4. Failures or risks.
5. Deviations from plan.
6. Next phase.

## Mandatory checkpoints

1. Documentation source of truth.
2. Source scaffold.
3. Legacy quarantine.
4. WorkrootEnvironment runtime.
5. Agent templates.
6. Storage/schema.
7. Core behavior.
8. Runtime flows.
9. Indexing.
10. Context Control.
11. Release Control protections.
12. Relationship Network.
13. Doctor.
14. CLI/install.
15. Tests.
16. Final docs and report.

## Stop conditions

Codex must stop and ask for review if:

- a legacy capability has no clear new owner;
- a migration would delete old files rather than quarantine;
- a test requires keeping active Public Seed layout;
- redaction/deletion protection cannot be enforced;
- contracts need to import core;
- implementation requires adding vector/search/remote LLM dependency;
- bootstrap-dev still requires root AGENTS/CLAUDE or `.workroot`.
