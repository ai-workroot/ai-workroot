# Scripts Directory

`scripts/` is not the active AI Workroot product implementation layer.

- `scripts/dev/` contains development, release validation, and review export helpers.

Active Clean Workroot behavior belongs in `src/ai_workroot/` and is invoked through
`python -m ai_workroot` or the installed `workroot` console script.

Runnable legacy Public Seed compatibility is not kept under `scripts/`. Historical
source snapshots live under `docs/history/public-seed/code-archive/` as
non-runnable archive material.
