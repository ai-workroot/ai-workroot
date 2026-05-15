# Kernel Implementation Specification

This document defines the AI Workroot kernel implementation.

It is the implementation-grade companion to `docs/ai-workspace-operating-system-design.md`. The OS design document explains the architecture and philosophy. This specification defines the concrete kernel layout, required files, contracts, schemas, registries, scripts, validation rules, and release gates.

## 1. Kernel Status

Kernel version source:

```text
.workroot/kernel/VERSION
```

Status:

```text
candidate
```

Implementation profile:

```text
file-first
JSON contracts
lightweight JSON schema descriptors
CSV registries
Python standard-library validation
optional rebuildable local data stores
```

The kernel is not an application server, hosted service, model provider, database product, or enterprise permission platform. It is the stable operating law of a Workroot.

## 2. Implementation Invariants

The public seed must expose the AI Workspace Operating System layout:

```text
space/ + .workroot/
```

The following invariants are binding:

- ordinary users work in `space/`
- kernel rules live in `.workroot/kernel/`
- optional capabilities live in `.workroot/extensions/`
- generated and operational state lives in `.workroot/runtime/`
- files are the source of truth
- generated stores are rebuildable accelerators
- identity content belongs in `space/profile/`
- internal task mechanics belong in `.workroot/runtime/work/`
- user-visible outputs belong in `space/work/`
- startup context stays small
- release, tombstone, redaction, and deletion decisions must be respected by generated stores
- public release validation must reject generated databases, caches, local metadata, private residue, and paths outside the public seed surface

## 3. Canonical Layout

The public seed layout is:

```text
ai-workroot/
  README.md
  START_HERE_FOR_HUMANS.md
  AGENTS.md
  CLAUDE.md
  PROJECT_BRIEF.md
  AUTHOR.md
  LICENSE
  NOTICE
  TRADEMARKS.md
  CONTRIBUTING.md
  DCO.md
  ROADMAP.md

  space/
    README.md
    profile/
      README.md
      profile.md
      roles.md
      values.md
      preferences.md
    work/
      README.md
      reports/
        README.md
    mind/
      README.md
      _templates/
      memory/
      knowledge/
      principles/
      decisions/
      patterns/
      reflections/
      invalidated/
      released/
    inbox/
      README.md
    files/
      README.md

  .workroot/
    README.md
    kernel/
      VERSION
      boot/
      contracts/
      schemas/
      interfaces/
      agent/
      config/
    extensions/
      capability_registry.csv
      capabilities/
      skills/
      mcp/
      adapters/
      drivers/
    runtime/
      context/
      work/
      index/
      data/
      cache/
      logs/

  docs/
  assets/
  scripts/
  tests/
  .github/
```

## 4. Source Of Truth

Durable truth lives in files.

Runtime stores and generated data may accelerate retrieval, analysis, and continuation, but they must not become canonical.

Rules:

- Markdown files hold human-readable doctrine, identity, work summaries, handoffs, knowledge, and explanations.
- JSON files hold machine-readable contracts, schemas, boot metadata, task metadata, and runtime context provenance.
- CSV files hold lightweight registries and relationship indexes.
- SQLite, DuckDB, full-text indexes, vector indexes, graph indexes, and caches are optional generated stores.
- Generated stores must be rebuildable from files and registries.
- Generated stores are not committed by default.
- Redaction, release, tombstone, and deletion decisions must propagate to generated stores.

## 5. Public Seed Surface

The public seed must be useful before any private material is added.

It may include:

- empty protocol anchors
- README files
- templates
- header-only registries
- empty runtime context files
- kernel contracts and schemas
- validation scripts
- public documentation

It must not include:

- private identity data
- real personal memory
- real team task history
- domain-specific operational residue
- generated SQLite, DuckDB, vector, graph, or cache stores
- local credentials
- external account settings
- unreviewed binary assets
- unfinished logo assets

Placeholders must be explicit and empty. The seed should invite ownership without pretending to be a real user's workspace.

## 6. Space Responsibilities

`space/` is user-owned and protocol-governed.

Required anchors:

```text
space/profile/
space/work/
space/mind/
space/inbox/
space/files/
```

Users may add other folders under `space/`. The kernel must not treat user-created folders as errors.

If user-created folders contain durable identity, work, knowledge, memory, decisions, source material, or continuation context, agents should connect that material back to the protocol anchors through summaries, links, indexes, or preservation actions.

### Identity

Canonical identity content:

```text
space/profile/
```

The kernel owns only the identity protocol:

- identity gate
- minimum identity expectations
- startup checks
- context summary policy
- compatibility rules for identity content

The kernel must not store the user's actual identity content in `.workroot/kernel/`.

Runtime may store compact identity summaries under `.workroot/runtime/context/`, but those summaries are derived state and must be rebuildable from `space/profile/`.

### Work

User-visible work:

```text
space/work/
```

Internal task mechanics:

```text
.workroot/runtime/work/tasks/<task-id>/
```

Ordinary users should not manage internal task mechanics.

### Mind

Long-term continuity:

```text
space/mind/
```

Mind may contain memory, knowledge, principles, decisions, patterns, reflections, invalidated beliefs, released context, and tombstones.

`space/mind/knowledge/` may be organized by the user's real domains. AI Workroot intentionally does not impose one universal second-level taxonomy.

## 7. Runtime Responsibilities

`.workroot/runtime/` is system-managed operational state.

Required runtime areas:

```text
.workroot/runtime/context/
.workroot/runtime/work/
.workroot/runtime/index/
.workroot/runtime/data/
.workroot/runtime/cache/
.workroot/runtime/logs/
```

### Context

Required files:

```text
.workroot/runtime/context/current.md
.workroot/runtime/context/handoff.md
.workroot/runtime/context/loaded-context.json
```

`current.md` and `handoff.md` must stay concise. `loaded-context.json` records context provenance and may be overwritten.

Minimum `loaded-context.json`:

```json
{
  "session_id": null,
  "updated_at": null,
  "loaded": []
}
```

### Internal Work

New internal task records live under:

```text
.workroot/runtime/work/tasks/<task-id>/
```

Rules:

- agents create and update internal work records when needed
- users do not need to request or manage task records
- task status lives in `task.json` and `task_registry.csv`, not in directory names
- `scratch.md` and archives are never default startup context
- closed task details are deep context
- user-facing outputs should be copied or summarized into `space/work/`
- legacy `active/` and `closed/` task paths may be read for compatibility, but new tasks use `tasks/`

Process levels:

- `L0`: lightweight task state for simple work
- `L1`: process records with plans, runs, retrieval cards, and checkpoints
- `L2`: evidence records with actions, recipes, validation, and invalidations

Internal task records may include:

```text
.workroot/runtime/work/tasks/<task-id>/task.json
.workroot/runtime/work/tasks/<task-id>/task.md
.workroot/runtime/work/tasks/<task-id>/brief.md
.workroot/runtime/work/tasks/<task-id>/todo.md
.workroot/runtime/work/tasks/<task-id>/decisions.md
.workroot/runtime/work/tasks/<task-id>/index.md
.workroot/runtime/work/tasks/<task-id>/handoff.md
.workroot/runtime/work/tasks/<task-id>/scratch.md
.workroot/runtime/work/tasks/<task-id>/plans/
.workroot/runtime/work/tasks/<task-id>/runs/
.workroot/runtime/work/tasks/<task-id>/actions/
.workroot/runtime/work/tasks/<task-id>/recipes/
.workroot/runtime/work/tasks/<task-id>/retrieval_cards/
.workroot/runtime/work/tasks/<task-id>/checkpoints/
.workroot/runtime/work/tasks/<task-id>/validation/
.workroot/runtime/work/tasks/<task-id>/invalidations/
.workroot/runtime/work/tasks/<task-id>/outputs/
.workroot/runtime/work/tasks/<task-id>/archive/
```

### Generated Data

`runtime/data/` may contain optional rebuildable data stores.

Recommended stores:

- SQLite for point lookup, relationships, and lightweight local state
- DuckDB for local analytical workloads
- full-text indexes for keyword retrieval
- vector indexes for semantic retrieval
- graph indexes for relationship traversal

Generated stores must be excluded from public release unless intentionally published as separate sample artifacts.

## 8. Kernel Versioning

Required version file:

```text
.workroot/kernel/VERSION
```

Required content:

```text
Current semantic version string, for example MAJOR.MINOR.PATCH.
```

Required kernel contract:

```text
.workroot/kernel/contracts/kernel.json
```

Required fields:

```json
{
  "contract_id": "kernel",
  "contract_version": "1.0.0",
  "kernel_version": "MAJOR.MINOR.PATCH",
  "schema_version": "1.0.0",
  "layout_version": "1.0.0",
  "interface_version": "1.0.0",
  "minimum_supported_kernel": "0.9.527",
  "status": "candidate",
  "source_of_truth": "files",
  "created_at": "YYYY-MM-DDTHH:MM:SSZ",
  "updated_at": "YYYY-MM-DDTHH:MM:SSZ"
}
```

Semantic versioning is used:

```text
MAJOR.MINOR.PATCH
```

Evolution rules:

- patch changes may fix wording, validation, and compatible tooling behavior
- minor changes may add optional fields, contracts, or interfaces
- major changes may change stable semantics and require an explicit compatibility plan
- public kernel changes must protect user-owned continuity

Stable kernel semantics:

- user space boundary
- kernel space boundary
- extension space boundary
- runtime space boundary
- file-first source of truth
- identity gate
- work visibility split
- boot context
- context budget
- permission hint semantics
- release, redaction, tombstone, and deletion semantics
- generated stores are rebuildable

## 9. Kernel Contracts

Required contract files:

```text
.workroot/kernel/contracts/kernel.json
.workroot/kernel/contracts/layout.json
.workroot/kernel/contracts/agent-startup.json
.workroot/kernel/contracts/context-policy.json
.workroot/kernel/contracts/forgetting-policy.json
.workroot/kernel/contracts/globalization-policy.json
.workroot/kernel/contracts/permission-hints.json
.workroot/kernel/contracts/storage-policy.json
.workroot/kernel/contracts/extension-policy.json
.workroot/kernel/contracts/test-policy.json
```

Every contract must include:

```json
{
  "contract_id": "example",
  "contract_version": "1.0.0",
  "schema_version": "1.0.0",
  "status": "candidate",
  "owner": "kernel",
  "updated_at": "YYYY-MM-DDTHH:MM:SSZ"
}
```

### `layout.json`

Defines required paths, optional paths, generated paths, space boundaries, and the allowed public seed root surface.

Validation must fail if required paths are missing. Release validation must fail if root-level paths outside the public seed surface exist.

### `agent-startup.json`

Defines the agent entrypoint, identity gate, default read-order contract, context budget, user interaction contract, and language policy.

The identity gate is required before formal durable work.

### `context-policy.json`

Defines context levels, default forbidden paths, startup file budget, startup character budget, and deep-context escalation.

Default startup must not load generated stores, caches, old task archives, raw data, or deep history.

### `forgetting-policy.json`

Defines release, tombstone, redaction, and deletion semantics.

Required rules:

- preserve useful lessons before release when possible
- forgetting is user-directed
- deletion requires explicit user choice
- `tombstone` is a first-class kernel term
- the current public seed reserves tombstone as a concept and interface, not a complete product workflow
- released, tombstone, and deleted material is excluded from normal retrieval
- generated stores must propagate release, tombstone, redaction, and deletion decisions

Required fields include:

```json
{
  "philosophy": "preserve_the_lesson_release_unnecessary_pain_keep_tombstones_by_choice",
  "user_choice_required": true,
  "default_release_level": "quiet",
  "deletion_requires_explicit_user_choice": true,
  "lesson_first": true,
  "tombstone_is_first_class": true,
  "tombstone_implementation_stage": "concept_and_interface_reservation",
  "tombstone_purpose": "intentional_remembrance_without_normal_reactivation",
  "future_tombstone_evolution_expected": true,
  "normal_retrieval_excludes": ["released", "tombstone", "deleted"]
}
```

### `globalization-policy.json`

Defines language, encoding, path, and time portability.

Rules:

- public docs are English
- machine-readable keys are English
- user interaction follows the latest user message language unless the user explicitly requests another language
- text encoding is UTF-8
- paths are repository-relative and use forward slashes
- precise machine-readable instants are stored as UTC ISO-8601
- local precise times require timezone or UTC offset before writing machine state

### `permission-hints.json`

Defines lightweight risk metadata for extensions, scripts, tools, and drivers.

AI Workroot uses permission hints, not ACL, RBAC, sandboxing, encryption policy, identity provider integration, or an enterprise permission UI.

Confirmation is required when actions are sensitive, destructive, secret-related, external-account-related, networked without user request, or writing to kernel space.

### `storage-policy.json`

Defines source-of-truth rules and generated store behavior.

Required rules:

- files are the source of truth
- generated stores are rebuildable
- generated stores are excluded from public release by default
- SQLite, DuckDB, full-text, vector, graph, and cache stores are optional accelerators
- release, redaction, tombstone, and deletion decisions propagate to generated stores

### `extension-policy.json`

Defines extension types, manifest requirements, registry path, and containment rules.

Extension types:

- capability
- skill
- MCP bridge
- agent adapter
- storage driver
- retrieval driver
- export/import driver

Extensions must not redefine identity, memory lifecycle, knowledge promotion, task lifecycle, privacy/release semantics, file-first source of truth, kernel versioning, or compatibility semantics.

### `test-policy.json`

Defines required validation commands and release blockers.

Release blockers include missing required paths, invalid contracts, invalid schemas, context-budget violations, paths outside the public seed surface, generated stores, private residue, timezone-free precise instants, invalid tombstone registry state, and deleted entries that retain source details.

## 10. Schemas

Required schema files:

```text
.workroot/kernel/schemas/kernel.schema.json
.workroot/kernel/schemas/layout.schema.json
.workroot/kernel/schemas/agent-startup.schema.json
.workroot/kernel/schemas/context-policy.schema.json
.workroot/kernel/schemas/forgetting-policy.schema.json
.workroot/kernel/schemas/globalization-policy.schema.json
.workroot/kernel/schemas/permission-hints.schema.json
.workroot/kernel/schemas/storage-policy.schema.json
.workroot/kernel/schemas/extension-policy.schema.json
.workroot/kernel/schemas/test-policy.schema.json
.workroot/kernel/schemas/read-order.schema.json
.workroot/kernel/schemas/context-budget.schema.json
.workroot/kernel/schemas/loaded-context.schema.json
```

Current schema files are lightweight JSON descriptors.

Each schema may declare:

- `schema_id`
- `schema_version`
- `target_contract`
- `required_fields`
- `field_types`
- `enum_values`
- `semver_fields`
- `timestamp_fields`
- `path_fields`

The validator supports a deterministic subset:

- required field checks
- primitive type checks
- enum checks
- semantic version checks
- UTC timestamp checks
- path safety checks

Full third-party JSON Schema validation may be added later as optional tooling.

## 11. Boot And Context Budget

Required boot files:

```text
.workroot/kernel/boot/boot.md
.workroot/kernel/boot/read-order.json
.workroot/kernel/boot/context-budget.json
```

`boot.md` is the compact startup law.

It must include:

- identity gate
- user simplicity rule
- context budget rule
- work and preservation rule
- extension loading rule
- sensitive action rule

`read-order.json` defines default and conditional startup context.

`context-budget.json` defines startup limits:

- maximum startup files
- maximum startup characters
- maximum loaded context records
- whether deep context requires a reason
- whether loaded context should be recorded

## 12. Registries

CSV is the default registry format.

Rules:

- UTF-8
- header row required
- repository-relative paths
- forward slash paths
- UTC ISO-8601 precise instants
- date-only lifecycle values are allowed where appropriate
- empty values are allowed for optional fields

Required registries:

```text
.workroot/runtime/index/task_registry.csv
.workroot/runtime/index/run_registry.csv
.workroot/runtime/index/action_registry.csv
.workroot/runtime/index/artifact_registry.csv
.workroot/runtime/index/decision_registry.csv
.workroot/runtime/index/retrieval_card_registry.csv
.workroot/runtime/index/checkpoint_registry.csv
.workroot/runtime/index/invalidation_registry.csv
.workroot/runtime/index/mind_registry.csv
.workroot/runtime/index/link_registry.csv
.workroot/extensions/capability_registry.csv
```

Required headers:

```text
task_registry.csv:
task_id,title,status,process_level,owner_scope,visibility,priority,created_at,updated_at,user_visible_output_path,source_path,brief_path,handoff_path,next_action

run_registry.csv:
run_id,task_id,title,status,validity,validity_reason,superseded_by,started_at,completed_at,output_dir,primary_artifact,validation,conclusion_preview,updated_at

action_registry.csv:
action_id,task_id,run_id,type,status,summary,tool,input_ref,output_ref,approval_ref,risk_level,created_at,updated_at

artifact_registry.csv:
artifact_id,task_id,run_id,action_id,type,path,audience,status,size,checksum,created_at,updated_at

decision_registry.csv:
decision_id,task_id,path,title,status,created_at,updated_at,promoted_path

retrieval_card_registry.csv:
card_id,task_id,path,freshness,source_paths,created_at,updated_at

checkpoint_registry.csv:
checkpoint_id,task_id,path,created_at,current_status,last_valid_run_id,next_action,required_context_paths

invalidation_registry.csv:
invalidation_id,task_id,run_id,artifact_id,invalidated_claim,reason,replacement_ref,path,created_at,updated_at

mind_registry.csv:
mind_id,title,type,status,temperature,privacy_level,release_level,retrieval_rule,created_at,updated_at,source_path,related_task_id,replaces_mind_id

link_registry.csv:
link_id,source_type,source_id,target_type,target_id,relation,created_at,updated_at

capability_registry.csv:
capability_id,name,type,status,owner,version,purpose,read_scope,write_scope,required_tools,optional_tools,privacy_level,source_path,created_at,updated_at
```

Registry headers are stable for the current public release line.

## 13. Mind Registry Semantics

Allowed Mind types:

```text
memory
knowledge
principle
decision
pattern
reflection
invalidated
released
tombstone
```

Allowed temperatures:

```text
hot
warm
cold
archived
released
tombstone
deleted
```

Allowed release levels:

```text
active
quiet
archived
tombstone
redacted
deleted
```

Tombstone consistency rule:

```text
If any of type, temperature, or release_level is tombstone,
then all three must be tombstone and retrieval_rule must be non-empty.
```

Deleted entry rule:

```text
Deleted entries must not retain source_path details.
```

Released, tombstone, and deleted entries require explicit retrieval rules.

## 14. Kernel Interfaces

Required interface files:

```text
.workroot/kernel/interfaces/agent-interface.md
.workroot/kernel/interfaces/capability-interface.md
.workroot/kernel/interfaces/export-import-interface.md
.workroot/kernel/interfaces/mcp-interface.md
.workroot/kernel/interfaces/privacy-interface.md
.workroot/kernel/interfaces/retrieval-interface.md
.workroot/kernel/interfaces/skill-interface.md
.workroot/kernel/interfaces/storage-interface.md
.workroot/kernel/interfaces/tool-interface.md
.workroot/kernel/interfaces/user-program-interface.md
```

Interfaces define stable expectations for replaceable implementations.

Each interface should specify:

- purpose
- allowed read scope
- allowed write scope
- required metadata
- permission hints
- source-of-truth rule
- context-loading rule
- confirmation rule
- failure behavior
- validation expectations

## 15. User Interaction And Work Lifecycle

The binding user interaction contract is:

```text
docs/user-interaction-contract.md
```

Ordinary users should experience:

```text
say what I want -> AI helps -> AI saves useful result -> I can continue later
```

Agents may create internal task records when:

- work has a goal
- work spans multiple steps
- work may need continuation
- work produces reusable output
- the user asks to save, continue, plan, review, or track

Users should not need to say "create a task."

Minimum task metadata:

```json
{
  "task_id": "task-YYYYMMDD-HHMMSS-slug",
  "title": "Task title",
  "status": "active",
  "created_at": "YYYY-MM-DDTHH:MM:SSZ",
  "updated_at": "YYYY-MM-DDTHH:MM:SSZ",
  "owner_scope": "personal",
  "visibility": "internal",
  "user_visible_output_path": null
}
```

Allowed task statuses:

```text
active
paused
blocked
closed
released
```

Allowed owner scopes:

```text
personal
team
role
organization
```

Before closing a task, agents should update the task brief, handoff, task metadata, relevant registries, user-visible outputs, and reusable Mind entries.

## 16. Kernel Scripts

Required script set:

```text
scripts/add_registry_row.py
scripts/workroot_client.py
scripts/workroot_cli.py
scripts/new_task.py
scripts/rebuild_sqlite.py
scripts/setup_workroot.py
scripts/test_new_task.py
scripts/validate_kernel.py
```

Script standards:

- Python 3
- standard-library-first
- deterministic
- cross-platform
- safe by default
- non-networked by default
- repository-relative paths
- clear error messages
- testable through `unittest` or deterministic scripts

Exit code conventions:

| Code | Meaning |
| --- | --- |
| `0` | success |
| `1` | validation failure or expected user-fixable error |
| `2` | invalid command usage |
| `4` | unsafe release state |

## 17. Validation

The canonical validator is:

```text
scripts/validate_kernel.py
```

It must validate:

- kernel version
- required contracts
- required schemas
- boot files
- context budget
- loaded-context structure
- required paths
- public seed surface in release mode
- registry headers
- registry time values
- forgetting and tombstone registry semantics
- generated store absence in release mode
- runtime cache/log cleanliness in release mode
- local metadata absence in release mode
- UTF-8 text files in release mode
- basic private residue patterns in release mode

Release mode:

```bash
python3 scripts/validate_kernel.py --release
```

Release mode is intentionally stricter than normal validation.

## 18. Compatibility And Evolution

The public seed is a native `space/ + .workroot/` system.

The kernel protects compatibility through stable boundaries:

- user space boundary
- kernel space boundary
- extension space boundary
- runtime space boundary
- file-first source of truth
- identity source of truth
- registry meanings
- context budget semantics
- release, redaction, tombstone, and deletion semantics

Future layout or contract changes must be additive when possible. If a future version requires semantic changes, it must provide a clear compatibility plan and validation before users are asked to adopt it.

## 19. Tests

Current test files:

```text
tests/test_kernel_contracts.py
tests/test_new_task.py
tests/test_public_seed_surface.py
```

Required test coverage:

- kernel version
- required contracts parse as JSON
- kernel validation succeeds
- release validation succeeds
- no root-level paths outside the public seed surface exist
- timezone-free precise instants are rejected
- timezone offsets are normalized to UTC
- multilingual task ids are supported
- invalid tombstone registry states are rejected
- deleted entries retaining source paths are rejected

Future test expansion should remain compatible with the current release gates and should not require ordinary users to install heavy dependencies.

## 20. Release Gates

Required release commands:

```bash
python3 -m py_compile scripts/*.py
python3 -m unittest discover tests
python3 scripts/validate_kernel.py
python3 scripts/validate_kernel.py --release
python3 scripts/test_new_task.py
git diff --check
```

If `scripts/rebuild_sqlite.py` is run during verification, the generated SQLite file must be removed before release validation and commit.

Release must block on:

- missing required paths
- invalid contract JSON
- invalid contract fields
- invalid schema descriptors
- context budget violation
- paths outside the public seed surface
- generated stores committed into the seed
- runtime cache or log artifacts committed into the seed
- private or domain-specific residue
- timezone-free precise instants in registries
- non-UTF-8 text files
- invalid tombstone registry state
- deleted entries retaining source details

## 21. Cross-Platform Requirements

AI Workroot must support macOS, Windows, and Linux.

Rules:

- repository paths use forward slashes
- contracts and registries use repository-relative paths
- scripts must avoid OS-specific shell assumptions
- text files are UTF-8
- precise machine-readable time is UTC ISO-8601
- local precise time input must include timezone or UTC offset before being written as machine state
- generated databases are optional and rebuildable

## 22. Globalization Requirements

Public repository documentation and machine-readable keys are English.

User interaction should use the language of the latest user message unless the user explicitly requests another language. Repository docs and machine-readable keys remain English.

Task titles and user content may be multilingual. Scripts must preserve Unicode where appropriate.

Machine-readable precise instants must use:

```text
YYYY-MM-DDTHH:MM:SSZ
```

Date-only lifecycle fields may use:

```text
YYYY-MM-DD
```

## 23. Definition Of Done

The kernel implementation is complete when:

- the canonical layout exists
- required contracts exist
- required schemas exist
- kernel version exists
- required registries exist with correct headers
- runtime context files exist
- work visibility split is implemented
- context budget is explicit
- permission hints are explicit
- forgetting policy is explicit
- globalization policy is explicit
- guided identity setup exists
- release validation exists
- public seed surface tests pass
- ordinary user docs remain simple
- generated stores and runtime artifacts are absent from the public seed
- root-level paths outside the public seed surface are absent from the public seed
- release gates pass

## 24. Implementation Rule

Implement the smallest rigorous kernel that can preserve continuity.

Everything else should remain an extension, driver, adapter, runtime accelerator, or future product layer.

The kernel must protect:

- identity
- intent routing
- work preservation
- knowledge promotion
- handoff
- context economy
- file-first source of truth
- release and tombstone semantics
- compatibility safety
- user-owned continuity
