# Runtime Layout

## User directory

The user-selected directory is a user asset directory.

Rules:

- AI Workroot does not treat same-named user folders such as `state/`, `logs/`, `cache/`, or `context/` as managed state.
- AI Workroot does not create internal runtime folders in the user directory by default.
- Native Agent Entry files are written only after explicit user authorization.
- Published Assets may be written to the user directory only through Asset Publication Policy.

Example:

```text
<user-directory>/
  user files...
  AGENTS.md   # only if authorized
  CLAUDE.md   # only if authorized
```

## AI_WORKROOT_HOME

`AI_WORKROOT_HOME` is represented by `WorkrootEnvironment`.

Target layout:

```text
$AI_WORKROOT_HOME/
  config.json

  registry/
    workroots.jsonl
    directory-bindings.jsonl
    aliases.jsonl
    relationships.jsonl
    .registry.lock

  preferences/
    operator-preferences.json
    policy-defaults.json
    agent-defaults/

  global-index/
    workroots.index.jsonl
    tasks.index.jsonl
    assets.index.jsonl
    decisions.index.jsonl
    handoffs.index.jsonl
    time.index.jsonl
    levels/

  global-cache/
    global.sqlite

  migrations/
    global.jsonl
    history/
    locks/

  concurrency/
    locks/

  workroots/
    wr_xxx/
      workroot.json
      charter/
      state/
      tasks/
      handoffs/
      assets/
      release/
      relationships/
      indexes/
      context/
      diagnostics/
      maintenance/
      cache/
      logs/
```

## Global layer rules

- `EnvironmentConfig`, `WorkrootRegistry`, `DirectoryBinding`, `Alias`, and `WorkrootRelationship` are canonical global state.
- `global-index` is a derived read model for navigation and management.
- `global-cache` is a derived/auxiliary store.
- No global knowledge body store.
- No global user profile. Use operator preferences and policy defaults only.
- Workroot role/persona/purpose belongs to `WorkrootCharter`.

## Per-Workroot rules

Each Workroot has:

- `workroot.json`: Workroot metadata.
- `charter/`: purpose, role, boundaries, collaboration rules.
- `tasks/`: task/process records where file-backed records are used.
- `assets/`: internal asset metadata or managed internal asset records.
- `release/`: release/tombstone/redaction/deletion records.
- `relationships/`: relationship network exports/backups if used.
- `indexes/`: per-Workroot derived indexes.
- `context/`: ContextPackage history and ContextTrace diagnostics.
- `diagnostics/`: doctor/check outputs.
- `cache/`: derived caches.

Runtime read views:

- SQLite at `cache/workroot.sqlite` is the canonical per-Workroot fact store.
- Files in `state/`, `tasks/`, `handoffs/`, `assets/`, `relationships/`, `indexes/`, `context/`, and `diagnostics/` are rebuildable read views or diagnostics.
- Protocol projection must not treat these read-view files as facts.
- `context/latest.md` is a bounded diagnostic preview, not a full context archive.
- `context/latest-trace.json` records whether the latest context preview was truncated.
- Current derived views include:

```text
state/current.json
tasks/current.json
tasks/active.json
handoffs/current.md
handoffs/current.json
assets/manifest.json
relationships/summary.json
indexes/manifest.json
context/latest.md
context/latest-trace.json
diagnostics/protocol-friction.json
```

## Protocol commit batches

- `protocol_commit_batches` and `protocol_events` are canonical SQLite facts.
- Version `0.9.531` supports atomic commit batches only.
- `atomic_batch=false` is a reserved future protocol mode. The controller rejects it before Workroot location or durable writes with `unsupported_atomic_batch_mode`.
- Agents may continue user-visible work after that rejection, then sync and retry with `atomic_batch=true` if durable persistence is still relevant.

## Source repository under bootstrap-dev

The AI Workroot source repository is a Clean Workroot user directory.

Active root must not contain tracked:

```text
AGENTS.md
CLAUDE.md
space/
.workroot/
.idea/
```

Allowed local-only:

```text
AGENTS.md
CLAUDE.md
.ai-workroot-local/
```

These must be ignored.

## `.ai-workroot-local/`

Purpose: local staging for bootstrap-dev.

```text
.ai-workroot-local/
  drafts/
  reviews/
  patches/
  smoke-output/
  context-packages/
```

Rules:

- Not managed state.
- Not formal source.
- Not committed.
- Formal content must be promoted into `docs/`, `src/`, `tests/`, `templates/`, or `.github/`.
