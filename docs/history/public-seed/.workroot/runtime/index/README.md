# Workroot Index

Indexes help AI agents find the right context without reading long historical logs.

## Core Registries

AI Workroot core registries are:

- `task_registry.csv`
- `run_registry.csv`
- `action_registry.csv`
- `artifact_registry.csv`
- `decision_registry.csv`
- `retrieval_card_registry.csv`
- `checkpoint_registry.csv`
- `invalidation_registry.csv`
- `mind_registry.csv`
- `link_registry.csv`

These files are part of the core protocol and are checked by `scripts/validate_kernel.py`.

## Capability Registries

Role or domain capabilities may add their own indexes when needed.

Examples:

- `batch_registry.csv`
- `experiment_registry.csv`
- `dataset_registry.csv`
- `customer_feedback_registry.csv`
- `scene_registry.csv`

Capability registries are allowed, but they are not part of the AI Workroot core schema. They should be documented and validated by the capability that owns them.

Do not weaken the core registries to fit one role-specific workflow. Add a capability-specific registry instead.

AI Workroot uses simple CSV files.

Future local databases, vector indexes, or graph indexes should be rebuildable from these file-based sources.

Long-lived registries should evolve toward lifecycle metadata such as `created_at`, `updated_at`, `status`, `temperature`, `confidence`, `last_used_at`, `review_after`, and `superseded_by`.

`task_registry.csv` records durable work units with `process_level`, `owner_scope`, visibility, source path, user-visible output path, brief path, handoff path, and next action.

The Work Process Layer uses `run_registry.csv`, `action_registry.csv`, `artifact_registry.csv`, `retrieval_card_registry.csv`, `checkpoint_registry.csv`, and `invalidation_registry.csv` to keep task process details findable without forcing startup context to load every process file.

Use `link_registry.csv` to connect tasks, artifacts, decisions, Mind entries, files, capabilities, and delegated sub-work. Do not add ownership or hierarchy columns to the core task registry for one workflow.

`temperature` marks retrieval policy. Use `hot`, `warm`, `cold`, `archived`, `released`, `tombstone`, or `deleted` when the registry supports it.

Released past context and tombstones are recorded through `mind_registry.csv` with `type`, `temperature`, `release_level`, and `retrieval_rule`.

`tombstone` entries are intentional memorial markers. They should stay out of normal retrieval and should contain no full painful detail.

For explicit deletion, the row may be removed or retained as a minimal deletion marker with an empty `source_path`. Do not use the index as a hidden archive of details the user chose to delete.

`link_registry.csv` records durable relationships between tasks, artifacts, decisions, Mind entries, files, and capabilities. Optional databases can import these links, but the CSV remains the source of truth.
