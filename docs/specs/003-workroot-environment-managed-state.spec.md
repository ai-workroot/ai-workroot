# Spec 003 — WorkrootEnvironment and Managed State

Status: accepted
Target: 0.9.530

## Purpose

Model `AI_WORKROOT_HOME` as `WorkrootEnvironment` and define global/per-Workroot state.

## Canonical global entities

- `EnvironmentConfig`
- `WorkrootRegistry`
- `WorkrootRegistration`
- `WorkrootDirectoryBinding`
- `WorkrootAlias`
- `WorkrootRelationship`
- `GlobalPreferences`
- `GlobalPolicyDefaults`

## Derived global entities

- `GlobalWorkrootIndex`
- `GlobalTaskIndex`
- `GlobalAssetIndex`
- `GlobalTimeIndex`
- `global-cache/global.sqlite`

## Target layout

```text
AI_WORKROOT_HOME/
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
  global-cache/
  migrations/
  concurrency/
  workroots/
```

## Global preferences rules

- No global user profile.
- No global knowledge body store.
- Global preferences are operator/system preferences: language, timezone, default context mode, default budgets, policy defaults.
- Per-Workroot role/purpose is stored in `WorkrootCharter`.

## Per-Workroot layout

```text
workroots/wr_xxx/
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

## Registry locking

All registry writes must hold `.registry.lock`.

Inside the lock, re-read registry before writing to avoid races.

## WorkrootRegistration vs Workroot

`WorkrootRegistration` lives in global registry. It points to user directory and state directory.

`Workroot` lives in per-Workroot state. It stores Workroot metadata and Workroot-level settings.

## Acceptance

- Environment initializes without global user profile.
- Registry writes are locked.
- Duplicate directory binding is race-safe.
- `global-index` is treated as derived read model.
- Doctor can detect registry-state mismatch.
