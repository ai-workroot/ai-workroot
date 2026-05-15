# Runtime Work

This folder holds internal work mechanics.

Ordinary users should not manage this folder manually. The AI agent creates and updates internal work records when a request has a goal, expected result, future value, or continuation need.

User-visible outputs, reports, and summaries belong in `space/work/`.

## Structure

```text
tasks/
_templates/
```

New task records live under `tasks/<task-id>/`. Task status lives in `task.json` and `.workroot/runtime/index/task_registry.csv`, not in directory names.

Older Workroots may contain `active/` and `closed/` directories. Those are legacy status-path directories. Agents and tools may read them for compatibility, but new tasks must not be created there.

## Process Levels

- `L0`: lightweight task state for simple work.
- `L1`: process records for multi-turn work with plans, runs, retrieval cards, and checkpoints.
- `L2`: evidence records for auditable work with actions, recipes, validation, and invalidations.

## Recommended Internal Files

```text
task.json
task.md
brief.md
decisions.md
todo.md
index.md
scratch.md
handoff.md
outputs/
archive/
```

L1 tasks add `plans/`, `runs/`, `retrieval_cards/`, and `checkpoints/`. L2 tasks also add `actions/`, `recipes/`, `data/`, `validation/`, and `invalidations/`.

`scratch.md` is an optional working scratchpad. It should not become a startup requirement.

`handoff.md` is the task-level continuation card. Keep it short enough for the next agent to resume without reading the full task history.

When a task closes, compress it into durable summaries, decisions, outputs, links, and promoted Mind entries. Move noisy process material into `archive/` so long-term context stays small.
