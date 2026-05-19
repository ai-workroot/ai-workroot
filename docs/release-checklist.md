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
- `docs/workroot-system-design.md` documents the user-space/kernel-space architecture.
- `docs/kernel-implementation-specification.md` defines the kernel versioning, contracts, schemas, validation behavior, tests, and release gates for implementation.
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
- The public seed uses the `space/ + .workroot/` architecture.
- Root-level paths outside the public seed surface are absent.
- Ordinary user docs describe `space/` as the visible user-owned space and do not instruct users to manage `.workroot/`.

## Global Readiness

- Task creation supports multilingual titles.
- File names and registry values use UTF-8.
- Machine-readable precise instants use ISO-8601 UTC text.
- User-provided local instants with explicit offsets can be normalized to UTC.
- Timezone-free precise instants are rejected in registries and contracts.
- The starter does not assume one country, language, job type, operating system, or AI agent.

## Protocol Integrity

- Files remain the source of truth.
- SQLite, DuckDB, vector indexes, and graph indexes remain optional rebuildable accelerators.
- Released, tombstone, redacted, and deleted material is not part of default retrieval.
- Durable lessons can survive even when painful source context is released.
- Tombstone remains a first-class kernel term and is not collapsed into generic archive semantics.
- Agent-specific memory does not replace Workroot files.
- Core registries are not weakened to fit a role-specific workflow.
- Capability-specific registries are documented by the owning capability.
- Extensions follow `docs/extension-contract.md`.
- Agents follow `docs/user-interaction-contract.md`.

## Validation

Run:

```bash
python3 -m py_compile scripts/*.py
python3 -m unittest discover tests
python3 scripts/validate_kernel.py
python3 scripts/validate_kernel.py --release
python3 scripts/test_new_task.py
python3 scripts/setup_workroot.py --help
git diff --check
```

The final status should contain only intentional release changes.

## 0.9.529 Clean Native Context Gates

- Clean Mode init creates no managed folders or control files inside the user-selected directory by default.
- Native Agent Entry files are created or modified only after explicit authorization.
- Managed state, indexes, context packages, handoffs, runtime data, logs, and debug traces live outside the user-selected directory by default.
- SQLite graph, candidate, and FTS tables are present in managed state.
- Context Guide runs locally, prints a Markdown Context Package, and does not require remote calls.
- Context Guide treats 1 second as the normal hot-path target, not a hard accuracy limit.
- Context Guide reads latency and token budgets from runtime hints or built-in defaults.
- Standard Mode is the default; Quality Mode is local and bounded; Deep Mode requires explicit request.
- Context Package includes mode, confidence, latency, token usage, fallback status, and low-confidence reasons when applicable.
- Codex, Claude, and default agent token budgets are represented and bounded.
- `AGENTS.md` and `CLAUDE.md` remain short launcher files and do not embed full Context Packages.
- Debug trace records resolution, mode, confidence, challengers, selected and dropped candidates, FTS matches, token budget, and timing.
- P0 retrieval does not require a vector database or remote embedding provider.
- `bootstrap-dev` creates no commits, tags, releases, or pushes automatically.
- `.ai-workroot-local/` is ignored and must not appear in release artifacts.
- Release validation rejects generated caches, SQLite stores, debug traces, local metadata, and private residue.
