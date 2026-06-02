# Roadmap

AI Workroot is currently in the 0.9.531 Agent Protocol and Task Continuity line, built on the 0.9.530 Clean Workroot architecture reset.

Public Seed is historical. The active product direction is personal, local-first Clean Workroot with managed state under `AI_WORKROOT_HOME`, clean user-selected directories by default, and a small Agent Protocol that lets AI agents `sync` and `commit` continuity facts without learning internal storage details.

The roadmap is organized by priority:

- P0: must be fixed or clarified before broader promotion
- P1: important next work after P0
- P2: medium-term product and protocol expansion
- P3: long-term directions

Within each priority level, the order in the table is the default execution order.

---

## P0 - Complete The First Stable Workroot Loop

| Order | Item | Type | Notes |
|---:|---|---|---|
| 1 | Keep Clean Mode strict | Engineering | User-selected directories stay clean by default; managed state stays under `AI_WORKROOT_HOME`. |
| 2 | Stabilize Agent Protocol continuity | Protocol / Engineering | Keep `sync` read-mostly, `commit` as the durable fact entry, and task ownership stable across agent turns. |
| 3 | Stabilize the package structure | Engineering | Keep command-first, protocol-runtime, capability-owned import boundaries enforced by tests. |
| 4 | Keep scripts closed over support roles | Engineering | `scripts/dev` is the only active scripts support surface; active product logic stays in `src/ai_workroot`. |
| 5 | Keep bootstrap-dev dogfood safe | Engineering | Source repo dogfood uses `workroot.project.json`, ignored Native Agent Entry files, and `.ai-workroot-local/` without commits, tags, or pushes. |
| 6 | Preserve legacy knowledge safely | History | Old Public Seed source is preserved as non-runnable history/fixtures, not as active root layout or runnable compatibility. |
| 7 | Harden Context Control | Product / Engineering | Keep local retrieval explainable, bounded, configurable, and free of mandatory vector, remote embedding, or remote LLM dependencies. Layered L1/L2/L3 recall remains the next major context strategy upgrade. |
| 8 | Complete release validation | Engineering | Release gates include unit, integration, smoke, negative, Clean Workroot doctor, archive boundary checks, and text audits. |
| 9 | Dogfood AI Workroot daily | Product | Use Clean Workroot and Agent Protocol flows to manage the AI Workroot project itself and real personal work. |

---

## P1 - Prepare The First Usable Product Loop

| Order | Item | Type | Notes |
|---:|---|---|---|
| 1 | Design the minimal Workroot Manager | Product | A personal manager for listing, opening, checking, and continuing Workroots. |
| 2 | Define Portable Mode separately | Product / Architecture | Portable state can be designed later; it must not weaken Clean Workroot defaults. |
| 3 | Improve Native Agent Entry onboarding | Protocol | Make authorized agent entry safe, short, path-safe, and easy to inspect. |
| 4 | Expand protocol transports carefully | Protocol | Keep the stable Agent Protocol semantics while adding MCP or SDK entry surfaces later. |
| 5 | Add real dogfooding examples | Documentation | Show how AI Workroot is used for the project itself and other real tasks. |
| 6 | Improve Start Here flow | Product | Make first use feel simple and non-technical. |

---

## P2 - Cross-Agent Integration

| Order | Item | Type | Notes |
|---:|---|---|---|
| 1 | Explore AI Workroot MCP Server | Integration | Let agents such as Hermes or Claude-compatible tools read Workroot state through MCP. |
| 2 | Define Workroot domain state model | Architecture | Clarify Work, Asset, Release Control, Relationship Network, Retrieval & Index Control, Context Control, Agent Interface, System Health, invalidation, and tombstone behavior. |
| 3 | Add Workroot doctor / repair concepts | Engineering | Detect broken structure, stale state, missing files, and invalid references. |
| 4 | Explore timeline and task views | Product | Hide internal protocol complexity behind user-friendly views. |
| 5 | Improve international documentation | Documentation | Keep English-first docs clear, concise, and globally understandable. |

---

## P3 - Long-Term Directions

| Order | Item | Type | Notes |
|---:|---|---|---|
| 1 | Desktop Workroot Manager | Product | A full desktop client for ordinary users. |
| 2 | Cross-device sync | Product / Infrastructure | Optional encrypted sync and backup. |
| 3 | Workroot templates and skills | Ecosystem | Optional templates for writing, coding, learning, research, life planning, and other uses. |
| 4 | Multi-agent handoff standard | Protocol | A broader standard for how different AI agents enter, use, and leave a Workroot. |
| 5 | Team version as separate product line | Product | Team collaboration is intentionally out of scope for the core personal product. |

---

## Current Focus

The current focus is P0.

Do not start building a full client until Clean Workroot, Agent Protocol continuity, and public architecture docs are healthy, readable, and consistent.
