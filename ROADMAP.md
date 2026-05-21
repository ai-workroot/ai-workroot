# Roadmap

AI Workroot is currently in the 0.9.530 Clean Workroot architecture reset.

Public Seed is historical. The active product direction is personal, local-first Clean Workroot with managed state under `AI_WORKROOT_HOME` and clean user-selected directories by default.

The roadmap is organized by priority:

- P0: must be fixed or clarified before broader promotion
- P1: important next work after P0
- P2: medium-term product and protocol expansion
- P3: long-term directions

Within each priority level, the order in the table is the default execution order.

---

## P0 - Complete The Clean Workroot Reset

| Order | Item | Type | Notes |
|---:|---|---|---|
| 1 | Keep Clean Mode strict | Engineering | User-selected directories stay clean by default; managed state stays under `AI_WORKROOT_HOME`. |
| 2 | Stabilize the package structure | Engineering | Keep `Core / Contracts / Runtime / Storage / Indexing / Agent / CLI` import boundaries enforced by tests. |
| 3 | Finish bootstrap-dev dogfood | Engineering | Source repo dogfood uses `workroot.project.json`, ignored Native Agent Entry files, and `.ai-workroot-local/` without commits, tags, or pushes. |
| 4 | Preserve legacy capabilities safely | Compatibility | Old Public Seed capabilities remain testable through history/fixtures, not active root layout. |
| 5 | Harden Context Control | Product / Engineering | Keep local retrieval explainable, bounded, configurable, and free of mandatory vector, remote embedding, or remote LLM dependencies. |
| 6 | Complete release validation | Engineering | Release gates include unit, integration, smoke, negative, Clean Workroot doctor, legacy compatibility, and text audits. |
| 7 | Dogfood AI Workroot daily | Product | Use Clean Workroot flows to manage the AI Workroot project itself and real personal work. |

---

## P1 - Prepare The First Usable Product Loop

| Order | Item | Type | Notes |
|---:|---|---|---|
| 1 | Design the minimal Workroot Manager | Product | A personal manager for listing, opening, checking, and continuing Workroots. |
| 2 | Define Portable Mode separately | Product / Architecture | Portable state can be designed later; it must not weaken Clean Workroot defaults. |
| 3 | Improve Native Agent Entry onboarding | Protocol | Make authorized agent entry safe, short, path-safe, and easy to inspect. |
| 4 | Define Codex / ChatGPT handoff format | Protocol | Make cross-AI handoff explicit and reusable. |
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

Do not start building a full client until the Clean Workroot reset is healthy, readable, and consistent.
