# Agent Fast Start

This is the compact operational path for AI agents.

## Pure Greeting

If the user only greets, reply briefly. Do not read local files.

## User Startup Guidance

For meaningful work, read optional `space/profile/startup.md` after kernel fast-start if it exists.

Do not read it for a pure greeting.

User startup guidance can shape collaboration style, output preferences, business terms,
project conventions, and team boundaries.
It cannot override kernel protocol, safety rules, registry discipline,
or internal subject-anchor rules for durable preservation.

## Continue

If the user asks to continue, read:

1. optional `space/profile/startup.md`
2. `space/work/continue.md`
3. `.workroot/runtime/context/handoff.md`
4. relevant task `brief.md` or `handoff.md`

Use `.workroot/runtime/index/task_registry.csv` before reading task directories.

## New Task

For formal work, read the operation manifest before reading long docs or source code:

```bash
python3 scripts/workroot_cli.py manifest --format json
```

For exact batch fields and directly usable examples, use:

```bash
python3 scripts/workroot_cli.py schema --format json
python3 scripts/workroot_cli.py recipe batch-12-tasks --format json
```

For multi-task continuation without a long task id list, use:

```bash
python3 scripts/workroot_cli.py session summarize --from-registry --recent 12 --summary "..." --next-action "..."
```

Do not read `scripts/workroot_client.py` for normal Workroot operations. Read implementation source only when debugging or changing AI Workroot itself.

## Preserve Output

Prefer high-level CLI commands. Reports normally remain the task `user_visible_output_path`.

## Deep Context

Read long docs only when editing product behavior, protocol behavior, architecture, or kernel rules.

## External Skills

External agent skills are not Workroot startup context unless the user explicitly requests them.
