# Workroot System Design

AI Workroot is a personal, local-first Workroot for individuals.

This document defines the public architecture as a durable system shape. It describes the product model, layer responsibilities, kernel boundaries, extension model, runtime model, and long-term design principles behind a user-owned Workroot.

For concrete file requirements, contracts, schemas, registry headers, scripts, and release gates, see `docs/kernel-implementation-specification.md`.

## 1. Purpose

AI Workroot exists to give AI-assisted work a durable home.

Most AI work disappears into disconnected chats. AI Workroot instead gives each person a portable Workroot where identity, work, memory, knowledge, decisions, handoff, and reusable context can accumulate over time.

The product promise is:

```text
You work in your space.
The AI helps you.
The kernel preserves continuity.
Your Workroot grows with you.
```

The architecture is built around one operating claim:

```text
User space stays simple.
Kernel space stays rigorous.
Extension space stays replaceable.
Runtime space stays rebuildable.
AI agents bridge the layers.
```

The user should be able to start by doing work. The kernel and agents should carry the structural discipline behind the scenes.

## 2. Scope

AI Workroot defines:

- a user-owned Workroot layout
- a kernel layout for contracts, schemas, interfaces, boot rules, and policies
- an extension layer for optional capabilities, skills, MCP bridges, agent adapters, and drivers
- a runtime layer for generated context, registries, caches, and rebuildable data stores
- an agent behavior model for identity setup, intent routing, preservation, handoff, and continuation
- a file-first source-of-truth model
- a context economy model for long-lived Workroots
- release, forgetting, redaction, deletion, and tombstone semantics
- globalization rules for language, encoding, time, and path portability

AI Workroot does not define:

- a hosted service
- a model provider
- a full application server
- enterprise access control
- a mandatory database architecture
- a required UI
- a complete emotional workflow for tombstones
- a replacement for human judgment

## 3. Design Principles

### Human First

The person remains the subject.

AI is a collaborator. Models, agents, tools, skills, MCP servers, databases, and clients are replaceable. The Workroot is the continuity layer that remains.

### Subject And Guidance

Before durable work begins, a Workroot must know who or what it serves.

Identity is not a rigid persona. It is the first anchor for context, values, preferences, boundaries, and long-term memory.

Identity content belongs to `space/profile/`. The kernel defines the identity gate and startup behavior, but it does not own the user's actual identity content.

### Simple For Users, Strict For Agents

Ordinary users should not need to learn the architecture before getting value.

Users say what they want to do. Agents route the work, preserve the useful results, maintain indexes, and leave handoff context.

The protocol stays strict behind the scenes.

### AI-Native Workroot System

AI Workroot is not a clone of a traditional operating system.

Traditional operating systems organize processes, files, devices, permissions, and system calls. AI Workroot organizes intention, identity, context, memory, knowledge, work, tools, retrieval, release, and continuity.

The central transition of an AI-native Workroot system is:

```text
human intention -> AI-assisted work -> useful result -> preserved meaning -> future continuation
```

### Stable Interfaces, Replaceable Implementations

AI tools will keep changing.

AI Workroot adapts by defining stable contracts and interfaces instead of depending on one model, one agent client, one database, or one protocol.

### File-First Source Of Truth

Durable truth lives in files.

Markdown, JSON, CSV, and user-owned source files are the durable substrate. SQLite, DuckDB, vector indexes, graph indexes, full-text indexes, and caches are accelerators. They must remain rebuildable.

### Context Economy

Long memory must not become large startup context.

AI Workroot must support years of accumulation without forcing every new session to read the whole past. Startup context stays small. Deeper memory is reached through summaries, registries, links, and retrieval.

### Open Workroot

The kernel protects a small set of anchors and lifecycle semantics. It must not limit what a person can build inside the Workroot.

User space and extensions may evolve in any domain-specific direction as long as they preserve the core continuity contracts.

## 4. Final Architecture

The public layout is:

```text
ai-workroot/
  README.md
  START_HERE_FOR_HUMANS.md
  AGENTS.md
  CLAUDE.md
  PROJECT_BRIEF.md
  AUTHOR.md
  LICENSE
  NOTICE
  TRADEMARKS.md
  CONTRIBUTING.md
  DCO.md
  ROADMAP.md

  space/
    README.md
    profile/
    work/
    mind/
    inbox/
    files/

  .workroot/
    README.md
    kernel/
      VERSION
      boot/
      contracts/
      schemas/
      interfaces/
      agent/
      config/
    extensions/
      capability_registry.csv
      capabilities/
      skills/
      mcp/
      adapters/
      drivers/
    runtime/
      context/
      work/
      index/
      data/
      cache/
      logs/

  docs/
  assets/
  scripts/
  tests/
  .github/
```

The architecture has four main spaces:

| Space | Path | Responsibility |
| --- | --- | --- |
| User space | `space/` | User-owned identity, work, mind, inbox, and files |
| Kernel space | `.workroot/kernel/` | Stable contracts, schemas, boot rules, interfaces, policies, and agent rules |
| Extension space | `.workroot/extensions/` | Optional capabilities, skills, MCP bridges, agent adapters, and drivers |
| Runtime space | `.workroot/runtime/` | Generated context, registries, internal work state, caches, logs, and rebuildable stores |

## 5. User Space

`space/` is the visible user-owned space.

It is user-owned and protocol-governed:

- the user owns the content
- the kernel owns the protocol
- runtime owns derived state

The stable anchors are:

```text
space/profile/
space/work/
space/mind/
space/inbox/
space/files/
```

Users may create additional folders inside `space/` for their own work:

```text
space/books/
space/company/
space/research/
space/health/
space/writing/
space/ideas/
```

The kernel must not treat these folders as errors. Agents should connect important material back to the stable anchors through summaries, links, indexes, or preserved outputs when useful.

### `space/profile/`

The subject identity.

It contains the visible identity content for the person:

- who or what this Workroot represents
- what role AI should play
- what work or life area it supports
- what values, preferences, and boundaries matter

`space/profile/` is the source of truth for identity content. Runtime may hold derived summaries, but those summaries are rebuildable and subordinate.

### `space/work/`

The user-visible work surface.

It holds summaries, reports, deliverables, and outputs that the user should naturally inspect. Internal task mechanics belong in runtime, not in the user's first mental model.

### `space/mind/`

The long-term externalized mind.

It contains:

- memory
- knowledge
- principles
- decisions
- patterns
- reflections
- invalidated beliefs
- released context
- tombstones

`space/mind/knowledge/` may be organized by the user's real domains. AI Workroot does not impose one universal second-level taxonomy.

### `space/inbox/`

Low-friction capture.

Users and agents can place unclassified ideas, links, files, notes, questions, and rough material here. Agents can later classify, preserve, link, or promote the material.

### `space/files/`

User-provided source materials and references.

Files are evidence and source material. They are not automatically durable knowledge. Agents should promote only the useful understanding that should survive beyond the file.

## 6. Kernel Space

`.workroot/kernel/` is the stable operating law of the Workroot.

Ordinary users should not need to manage it.

The kernel defines contracts, not implementations. It preserves meaning, compatibility, startup discipline, privacy semantics, release semantics, context economy, and extension boundaries.

### Boot

Path:

```text
.workroot/kernel/boot/
```

Boot files define the smallest startup surface:

- what agents read first
- what agents do not read by default
- how much context can be loaded
- how to escalate into deeper context

Required boot files:

```text
boot.md
read-order.json
context-budget.json
```

### Contracts

Path:

```text
.workroot/kernel/contracts/
```

Contracts are compact machine-readable kernel policy.

Required kernel contracts:

```text
kernel.json
layout.json
agent-startup.json
context-policy.json
forgetting-policy.json
globalization-policy.json
permission-hints.json
storage-policy.json
extension-policy.json
test-policy.json
```

Markdown explains. JSON declares and validates.

### Schemas

Path:

```text
.workroot/kernel/schemas/
```

Schemas define the required structure for contracts, boot files, and runtime context records.

The current kernel uses lightweight JSON schema descriptors validated by standard-library Python. A full third-party JSON Schema engine may be added later as optional tooling without changing the public contract semantics.

### Interfaces

Path:

```text
.workroot/kernel/interfaces/
```

Interfaces define how replaceable capabilities connect without invading the kernel.

Current interface families include:

- capability interface
- skill interface
- MCP interface
- tool interface
- agent interface
- storage interface
- retrieval interface
- privacy interface
- export/import interface
- user program interface

The interface layer is the system-call boundary of AI Workroot.

### Agent Rules

Path:

```text
.workroot/kernel/agent/
```

Agent rules define startup behavior, memory policy, routing, and output style for AI agents working inside a Workroot.

The agent is the primary product interface for ordinary users.

### Config

Path:

```text
.workroot/kernel/config/
```

Config documents define human-readable policy for:

- context
- forgetting
- governance
- lifecycle
- local runtime
- privacy
- storage
- time
- tools

## 7. Extension Space

`.workroot/extensions/` is the replaceable capability layer.

Extensions may add power, but they must not redefine:

- identity
- memory lifecycle
- knowledge promotion
- task lifecycle
- privacy and release semantics
- file-first source of truth
- kernel versioning
- compatibility semantics

Current extension areas:

```text
.workroot/extensions/capabilities/
.workroot/extensions/skills/
.workroot/extensions/mcp/
.workroot/extensions/adapters/
.workroot/extensions/drivers/
.workroot/extensions/capability_registry.csv
```

Extension types include:

- capability
- skill
- MCP bridge
- agent adapter
- storage driver
- retrieval driver
- export/import driver

Every non-trivial extension should declare its purpose, read scope, write scope, privacy level, required tools, optional tools, runtime stores, and rebuild behavior.

Extensions can evolve faster than the kernel, but they must remain contained by kernel interfaces.

## 8. Runtime Space

`.workroot/runtime/` holds generated or operational state.

Runtime is system-managed. Ordinary users should not need to edit it directly.

Runtime areas:

```text
.workroot/runtime/context/
.workroot/runtime/work/
.workroot/runtime/index/
.workroot/runtime/data/
.workroot/runtime/cache/
.workroot/runtime/logs/
```

### Context

`runtime/context/` stores compact continuation state:

- `current.md`
- `handoff.md`
- `loaded-context.json`

These files must remain short. They exist to help an agent continue without reading the whole Workroot.

### Work

`runtime/work/` stores internal task mechanics.

User-visible outputs belong in `space/work/`. Internal task records belong in runtime.

### Index

`runtime/index/` stores CSV registries:

- task registry
- artifact registry
- decision registry
- mind registry
- link registry

Registries make the Workroot navigable and rebuildable. They are not a replacement for durable source files.

### Data

`runtime/data/` stores optional rebuildable local stores:

- SQLite
- DuckDB
- full-text indexes
- vector indexes
- graph indexes

Storage choices are drivers. They are not kernel identity.

### Cache And Logs

Caches and logs are operational state.

They must not become hidden archives of material the user has released, tombstoned, redacted, or deleted.

## 9. Agent Product Model

The AI agent is the user-facing product interface.

The user speaks naturally. The agent handles:

- onboarding
- identity setup
- intent routing
- task organization
- result preservation
- knowledge promotion
- release and forgetting
- handoff
- continuation

The first user journey is:

```text
download or clone -> rename outer folder -> open with AI -> define identity -> do first work -> save what matters -> continue later
```

The agent should not require ordinary users to understand internal folders, registries, schemas, databases, or task mechanics before getting value.

## 10. Intent Routing

Agents should infer the lightest suitable path:

| Intent | Behavior |
| --- | --- |
| Quick question | Answer directly, offer to preserve if useful |
| Work with a goal | Create or update internal task state when needed |
| Larger effort | Break down, start the first useful step, preserve handoff |
| Decision | Compare, choose, record why |
| Learning | Explain, then preserve reusable understanding |
| Preservation | Save result, decision, memory, knowledge, principle, pattern, reflection, invalidation, release marker, or handoff |
| Continuation | Read current context and handoff, then resume |
| Release or forgetting | Preserve the lesson first, then quiet, tombstone, redact, or delete by user choice |

Users should not need to name these modes.

## 11. Mind Model

Mind is the long-term continuity layer.

It separates different kinds of durable context:

| Type | Meaning |
| --- | --- |
| Memory | What happened |
| Knowledge | What can be reused |
| Principle | What should guide future action |
| Decision | What was chosen and why |
| Pattern | What repeats over time |
| Reflection | What the experience means |
| Invalidated | What used to be believed but should no longer guide action |
| Released | What no longer needs active recall |
| Tombstone | A minimal marker for remembrance without normal reactivation |

Mind entries should be discoverable through files, registries, links, and optional retrieval drivers.

## 12. Forgetting And Tombstones

AI Workroot is designed to remember, but a healthy mind also needs to release.

The default philosophy is:

```text
Preserve the lesson.
Release the unnecessary pain.
Live in the present.
Move toward the future.
```

Forgetting is user-directed. Deletion requires explicit user choice.

`tombstone` is a first-class kernel term. In the current public seed it is a concept and interface reservation, not a complete product workflow.

A tombstone is an intentional marker for remembrance, mourning, closure, or responsibility without keeping the full raw context active.

Future versions may deepen tombstone behavior through philosophy, product workflow, UI, lifecycle audits, export/import rules, and generated-store cleanup. That evolution must remain user-directed and backward-compatible with existing tombstone markers.

## 13. Context Economy

AI Workroot must support long memory without large startup context.

Default startup should load:

- agent entrypoint
- human start guide
- boot file
- read order
- user interaction contract
- concise current context and handoff when continuing

Default startup should not load:

- generated databases
- caches
- old task scratch files
- closed task archives
- raw data
- released context
- tombstones
- every extension

Context is loaded progressively:

| Level | Name | Default |
| --- | --- | --- |
| L0 | Boot | yes |
| L1 | Active context | yes when relevant |
| L2 | Indexes | no |
| L3 | Focused kernel docs | no |
| L4 | Extensions | no |
| L5 | Deep history | explicit reason only |

## 14. Storage And Retrieval

Files remain the source of truth.

Generated stores are optional accelerators:

- SQLite for local lookup and relationships
- DuckDB for local analytical workloads
- full-text search for keyword retrieval
- vector indexes for semantic retrieval
- graph indexes for relationship traversal
- caches for disposable acceleration

Generated stores must be rebuildable and excluded from public release by default.

Release, tombstone, redaction, and deletion decisions must propagate to derived stores.

## 15. Global Readiness

AI Workroot is global by default.

Rules:

- public repository docs are English
- machine-readable keys are English
- user interaction follows the language of the latest user message unless the user explicitly requests another language
- text files use UTF-8
- paths are repository-relative and use forward slashes
- precise machine-readable instants use UTC ISO-8601
- local precise times require timezone or UTC offset before being written as machine state
- date-only lifecycle values are allowed where no precise instant is needed

## 16. Compatibility And Evolution

AI Workroot protects continuity through stable boundaries:

- user space boundary
- kernel space boundary
- extension space boundary
- runtime space boundary
- identity source of truth
- file-first source of truth
- registry meaning
- context budget
- release and tombstone semantics

Future changes should be additive when possible:

- add fields instead of renaming fields
- add contracts instead of rewriting contracts
- add interface versions instead of mutating interfaces in place
- add compatibility helpers before requiring layout changes
- keep old fields readable until a major version boundary

Breaking semantic changes require a version boundary, compatibility plan, and validation.

## 17. Success Criteria

AI Workroot is successful when:

- ordinary users can begin without reading architecture docs
- agents can follow strict startup, identity, preservation, and handoff rules
- user-owned content remains portable
- generated stores remain rebuildable
- old context does not pollute startup context
- extensions can add power without weakening the kernel
- forgetting and tombstones are respected without heavy implementation
- future kernel evolution has stable boundaries

The result should feel like a simple personal Workroot to ordinary users and a rigorous operating protocol to agents and contributors.
