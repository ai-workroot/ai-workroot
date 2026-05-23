# Development Scripts

This directory contains developer-only helpers, release validation wrappers, and
review export tools.

These scripts may call package code under `src/ai_workroot/`, but they are not
the product implementation surface.

Use `scripts/dev/setup-dev.sh` to create a local development virtual environment
and install developer-only tools such as Ruff. Release validation expects the
developer environment to be prepared explicitly; it must not install tools as an
implicit side effect.

Do not add runnable legacy Public Seed compatibility here. Legacy source belongs
only in the non-runnable historical archive under
`docs/history/public-seed/code-archive/`.
