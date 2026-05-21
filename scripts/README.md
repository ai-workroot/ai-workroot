# Scripts Directory

`scripts/` is not the active AI Workroot product implementation layer.

- `scripts/dev/` contains development, release validation, review export, and smoke helpers.
- `scripts/compat/` contains short compatibility wrappers that call `src/ai_workroot/`.
- `scripts/legacy/public_seed/` contains quarantined Public Seed compatibility entry points.

Active Clean Workroot behavior belongs in `src/ai_workroot/` and is invoked through
`python -m ai_workroot` or the installed `workroot` console script.
