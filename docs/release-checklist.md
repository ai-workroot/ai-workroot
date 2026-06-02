# Public Release Checklist

Use this checklist before publishing or tagging AI Workroot as a public open-source seed.

Release tag:

```text
vX.Y.Z
```

## Repository Cleanliness

- No private identity, personal address, phone number, email, token, secret, or private account data.
- No real user task, note, report, dataset, work artifact, or conversation residue.
- No generated local databases or caches.
- No IDE metadata, operating-system metadata, or temporary files.
- No unfinished logo, image, or brand asset.
- No domain-specific assumption in the core seed.
- No local runtime secret, MCP server definition, private agent setting, or credential file.
- `LICENSE` is Apache-2.0.
- `NOTICE` preserves project name, domain, and brand boundaries.
- `TRADEMARKS.md` explains allowed and restricted brand use.
- `DCO.md` explains contribution rights.
- Name and trademark clearance has been checked for `AI Workroot`, `Workroot`, and planned official variants.
- GitHub repository description and topics follow `docs/launch-and-discovery.md`.
- Contributor contact and maintainer expectations are clear in `CONTRIBUTING.md`.
- `docs/good-first-issues.md` gives concrete starter contributions.
- `docs/who-we-are-looking-for.md` explains contributor roles and long-term maintainer expectations.
- GitHub issue and pull request templates exist under `.github/`.

## User Experience

- README stays short enough for ordinary users to begin.
- `START_HERE_FOR_HUMANS.md` gives a clear first message.
- `docs/user-sop.md` provides a practical operating manual without adding demo data to the core template.
- `docs/product-experience.md` defines first run, intent routing, continue, and save-what-matters behavior.
- `docs/workroot-system-design.md` documents the Clean Workroot architecture.
- `docs/kernel-implementation-specification.md` defines Clean Workroot implementation requirements, validation behavior, tests, and release gates.
- `docs/user-interaction-contract.md` defines the ordinary-user interaction contract.
- `docs/architecture-map.md` provides a visual explanation of the protocol.
- `docs/daily-loop.md` explains the everyday operating rhythm.
- New users are invited to rename only the outer folder into something personal before first use.
- New users are told not to rename internal protocol folders.
- Identity setup is required before formal work, but it remains lightweight.
- Users can ask quick questions without understanding the internal architecture.
- Agents infer when work should become an internal task record; ordinary users are not asked to manage task files or indexes.
- Users can say `Help me continue.` and `Save what matters.` without learning internal structures.
- Users can ask what tasks have been done before and receive a local task summary.
- Agents respond in the user's latest language unless the user explicitly requests another language.
- A new user can start from the README without reading architecture documents first.
- Public Seed is historical; active release root does not track `space/`, `.workroot/`, root `AGENTS.md`, or root `CLAUDE.md`.
- Root-level paths outside the public seed surface are absent.
- Ordinary user docs describe clean user-selected directories and do not instruct users to manage internal state.

## Global Readiness

- Task creation supports multilingual titles.
- File names and registry values use UTF-8.
- Machine-readable precise instants use ISO-8601 UTC text.
- User-provided local instants with explicit offsets can be normalized to UTC.
- Timezone-free precise instants are rejected in registries and contracts.
- The starter does not assume one country, language, job type, operating system, or AI agent.

## Protocol Integrity

- Managed SQLite is the canonical system fact store for Workroot runtime facts.
- Runtime read views are rebuildable files derived from managed SQLite facts.
- User-visible asset files remain user-owned outputs, not protocol runtime state.
- DuckDB, vector indexes, remote embeddings, and graph databases are not required active dependencies.
- Released, tombstone, redacted, and deleted material is not part of default retrieval.
- Durable lessons can survive even when painful source context is released.
- Tombstone remains a first-class kernel term and is not collapsed into generic archive semantics.
- Agent-specific private recall does not replace Workroot-managed state and Assets.
- Core registries are not weakened to fit a role-specific workflow.
- Capability-specific registries are documented by the owning capability.
- Extensions follow `docs/extension-contract.md`.
- Agents follow `docs/user-interaction-contract.md`.

## Validation

Run:

```bash
python3 -m py_compile $(find src scripts tests -name "*.py")
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m ai_workroot doctor --release
scripts/dev/validate-release.sh
git diff --check
```

Default release validation does not run E2E, longrun, or live-agent tests.
Run E2E only when explicitly requested:

```bash
AI_WORKROOT_RUN_E2E=1 python3 -m tests.e2e.runner --suite safety
AI_WORKROOT_RUN_E2E=1 python3 -m tests.e2e.runner --suite persona-smoke
AI_WORKROOT_RUN_E2E=1 python3 -m tests.e2e.runner --suite longrun
```

Windows PowerShell parse validation is pending unless a Windows CI job or local `pwsh` check parses `install/windows/install.ps1` and `scripts/dev/bootstrap-dev.ps1`.

The final status should contain only intentional release changes.

## 0.9.531 Current Release Gates

- Clean Mode init creates no managed folders or control files inside the user-selected directory by default.
- Native Agent Entry files are created or modified only after explicit authorization.
- Managed state, indexes, context packages, handoffs, runtime data, logs, and debug traces live outside the user-selected directory by default.
- Agent Protocol actions remain limited to `sync` and `commit`.
- `sync` does not create durable Task, TaskRun, lease, or event facts.
- Durable task continuity facts enter through `commit`.
- Quick work does not create durable Workroot facts.
- Runtime read views under tasks, handoffs, assets, relationships, indexes, context, diagnostics, and state are rebuildable.
- SQLite Relationship Network, candidate, and FTS tables are present in managed state.
- Context Control runs locally, prints a Markdown Context Package, and does not require remote calls.
- Context Control treats 1 second as the normal hot-path target, not a hard accuracy limit.
- Context Control reads latency and token budgets from runtime hints or built-in defaults.
- Context Control token usage estimates the full Context Package, not only selected candidates.
- Context Control uses query, candidate FTS, file FTS, and related one-hop Relationship Network signals to influence selection or scoring.
- Standard Mode is the default; Quality Mode is local and bounded; Deep Mode requires explicit request.
- If Quality Mode only expands candidate budget, debug trace labels it as `quality-budget-expansion`.
- Context Package includes mode, confidence, latency, token usage, fallback status, and low-confidence reasons when applicable.
- Codex, Claude, and default agent token budgets are represented and bounded.
- `AGENTS.md` and `CLAUDE.md` remain short launcher files and do not embed full Context Packages.
- Follow-up: continue splitting `src/ai_workroot/context/builder.py` budget, token, render, and trace logic into smaller focused package modules.
- Debug trace records resolution, mode, confidence, challengers, selected and dropped candidates, FTS matches, token budget, and timing.
- P0 retrieval does not require a vector database or remote embedding provider.
- `bootstrap-dev` creates no commits, tags, releases, or pushes automatically.
- `bootstrap-dev` initializes SQLite and supports `context` and `doctor` immediately after bootstrap.
- Install scripts are documented as CLI wrapper installers unless full first-run setup is implemented.
- Runnable legacy Public Seed compatibility is removed from active paths; historical snapshots are inspectable under `docs/history/public-seed/code-archive/`.
- `scripts/` root contains no Python product implementation files; support scripts live under `scripts/dev`.
- `.ai-workroot-local/` is ignored and must not appear in release artifacts.
- Release validation rejects generated caches, SQLite stores, debug traces, local metadata, and private residue.
