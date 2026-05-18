# Roadmap

AI Workroot is currently an early public seed.

The roadmap is organized by priority:

- P0: must be fixed or clarified before broader promotion
- P1: important next work after P0
- P2: medium-term product and protocol expansion
- P3: long-term directions

Within each priority level, the order in the table is the default execution order.

---

## P0 - Stabilize The Public Seed

| Order | Item | Type | Notes |
|---:|---|---|---|
| 1 | Restore source formatting | Engineering | Markdown and Python files must be readable, reviewable, and not collapsed into giant lines. |
| 2 | Verify scripts and tests | Engineering | Run py_compile, unit tests, and release validation. |
| 3 | Remove old tool-centered positioning | Positioning | Position AI Workroot as personal, local-first, user-owned, and agent-neutral. |
| 4 | Replace mandatory upfront identity wording | Product | Use progressive guidance: start first, clarify over time. |
| 5 | De-emphasize archived founding notes | Documentation | Keep project-philosophy.md as canonical; keep early founding intention notes out of the primary navigation. |
| 6 | Clarify current public seed architecture | Documentation | Make clear that space/ + .workroot/ is the current transparent seed, while future clients may support Clean Mode. |
| 7 | Dogfood AI Workroot daily | Product | Use AI Workroot to manage the AI Workroot project itself and real personal work. |

---

## P1 - Prepare The First Usable Product Loop

| Order | Item | Type | Notes |
|---:|---|---|---|
| 1 | Discuss and design the minimal Workroot Client | Product | Deferred until after P0. Do not implement in this task. |
| 2 | Define Clean Mode and Portable Mode | Product / Architecture | Clean Mode keeps visible user directories clean; Portable Mode carries Workroot state with the directory. |
| 3 | Define Workroot Manager | Product | A personal manager for listing, opening, checking, and continuing Workroots. |
| 4 | Define Codex / ChatGPT handoff format | Protocol | Make cross-AI handoff explicit and reusable. |
| 5 | Add real dogfooding examples | Documentation | Show how AI Workroot is used for the project itself and other real tasks. |
| 6 | Improve Start Here flow | Product | Make first use feel simple and non-technical. |

---

## P2 - Cross-Agent Integration

| Order | Item | Type | Notes |
|---:|---|---|---|
| 1 | Explore AI Workroot MCP Server | Integration | Let agents such as Hermes or Claude-compatible tools read Workroot state through MCP. |
| 2 | Define Workroot state model | Architecture | Clarify state, decisions, handoff, memory, invalidation, release, and tombstone. |
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

Do not start building the Client until the public seed is healthy, readable, and consistent.
