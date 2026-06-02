# protocol/

`protocol/` implements the Workroot Agent Protocol runtime.

It sits below command adapters and above capability modules:

```text
commands/ -> protocol/ -> work/, handoff/, context/, assets/, relationships/, release/, retrieval/, state/
```

## What Belongs Here

It contains protocol spec objects:

- `model.py`: sync and commit request/response model objects.
- `events.py`: canonical protocol event validation and hashing helpers.

Runtime implementation:

- `controller.py`: sync/commit orchestration.
- `focus.py`: semantic focus resolution for sync.
- `work_signal.py`: normalized work-signal hints.
- `lease.py`: lease minting, validation, and state-version checks.
- `response.py`: model-facing response construction.
- `recovery.py`: non-blocking recovery responses.
- `projections.py`: protocol event projection routing into capability facts.
- `packet.py`: private packet rendering for model-visible exchange guidance.

## Rules

Allowed:

- `protocol -> state`
- `protocol -> work`
- `protocol -> handoff`
- `protocol -> context` for continuity reads and startup context presentation
- `protocol -> assets`, `release`, `relationships`, or `retrieval` when a protocol event needs those capability outputs

Forbidden:

- Capability modules importing `protocol/`.
- `protocol/` importing `cli/`.
- Protocol request or response models leaking into lower capability state machines.
- SQLite paths, runtime internals, and state-version details being exposed as model-facing guidance.

The Agent Protocol is the application control layer for agent interaction. It does not own Task, Handoff, Context, Release, Retrieval, Relationship, or Asset truth.
