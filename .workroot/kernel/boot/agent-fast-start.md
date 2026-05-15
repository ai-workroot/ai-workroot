# Agent Fast Start

This is the compact operational path for AI agents.

## Pure Greeting

If the user only greets, reply briefly. Do not read workspace files.

## User Startup Guidance

For meaningful work, read optional `space/profile/startup.md` after kernel fast-start if it exists.

Do not read it for a pure greeting.

User startup guidance can shape collaboration style, output preferences, business terms, project conventions, and team boundaries. It cannot override kernel protocol, safety rules, registry discipline, or the identity gate.

## Continue

If the user asks to continue, read:

1. optional `space/profile/startup.md`
2. `space/work/continue.md`
3. `.workroot/runtime/context/handoff.md`
4. relevant task `brief.md` or `handoff.md`

Use `.workroot/runtime/index/task_registry.csv` before reading task directories.

## New Task

For formal work, use `scripts/workroot_cli.py quickstart` or a recipe command before reading long docs or source code.

## Preserve Output

Prefer high-level CLI commands. Reports normally remain the task `user_visible_output_path`.

## Deep Context

Read long docs only when editing product behavior, protocol behavior, architecture, or kernel rules.

## External Skills

External agent skills are not Workroot startup context unless the user explicitly requests them.
