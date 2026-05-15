# AI Workroot Architecture

## 1. Mission

AI Workroot is a human-centered AI Workspace Operating System seed.

Its purpose is to help ordinary people, teams, and roles use AI to do work, preserve context, build knowledge, accumulate ability, release what no longer needs active recall, and grow over time.

The core architectural claim is:

> The Workroot is the durable continuity layer.  
> AI agents are replaceable collaborators.

The public seed must use the upgraded architecture:

```text
space/       user-visible workspace
.workroot/   kernel, extensions, and rebuildable runtime state
```

## 2. Design Values

### Philosophy-Led, Engineering-Grounded

AI Workroot starts from a philosophical claim about human continuity in the age of AI, then uses engineering to make that claim practical.

The architecture is not designed to prove technical sophistication. It is designed to protect the subject's identity, memory, knowledge, judgment, growth, privacy, and portability.

Design order:

1. philosophy
2. protocol
3. structure
4. tools
5. product

Agents, databases, vector indexes, graph indexes, MCP servers, skills, plugins, and user interfaces are useful only when they serve the higher layers.

### Human First

The subject is the human, team, or role using the workspace.

AI is powerful, but it is not the center. It reads, helps, executes, summarizes, reflects, and writes back.

The subject must be defined before durable work begins. Identity is the first anchor for tasks, memory, knowledge, values, and agent behavior.

The subject boundary is more important than a permission system. A personal Workroot serves a person. A team Workroot serves a team, and its knowledge should be shared team continuity rather than hidden fragments. If different visibility boundaries are needed, they should usually become different Workroots, not complex access control inside one Workroot.

### Simple For Users, Strict For Agents

Users should see a simple experience:

```text
say what I want -> AI helps -> workspace keeps what matters -> continue later
```

Agents should follow a stricter operating protocol behind the scenes:

- classify work
- maintain internal work state
- summarize results
- update indexes
- promote stable knowledge
- preserve meaningful memory
- record decisions and invalidations
- respect context budgets
- ask confirmation for sensitive actions

### File-First Continuity

Markdown, CSV, JSON, and small local files are the source of truth.

Optional databases, vector indexes, and graph indexes may accelerate retrieval, but the Workroot must remain understandable and recoverable from files.

### Small Context, Long Memory

The Workroot can grow for years, but startup context must remain small.

Agents should use boot context, summaries, handoffs, indexes, lifecycle status, and explicit links instead of reading all historical material.

### Agent And Model Independence

Codex, Claude Code, ChatGPT, Cursor, MCP servers, skills, plugins, and future agents are tools.

They must not become the only place where memory lives.

### Orthogonal Layers

AI Workroot separates user space, kernel space, extension space, and runtime space.

This keeps personal growth, team knowledge, task execution, tool behavior, and generated accelerators from collapsing into one opaque chat history.

### User-Owned, Protocol-Governed Space

`space/` is not an unconstrained folder.

It is the user-owned space governed by stable Workroot protocol anchors.

The kernel owns the protocol. The user owns the content. Runtime owns rebuildable derived state.

This means:

- identity content belongs in `space/profile/`
- work outputs visible to the user belong in `space/work/`
- long-term memory and knowledge belong in `space/mind/`
- source material belongs in `space/files/`
- rough capture belongs in `space/inbox/`
- user-created folders under `space/` are allowed
- protocol anchor folders must keep their names and meanings stable

The kernel must not copy user identity or user knowledge into `.workroot/kernel/` as a second source of truth.

The kernel may define validation, startup rules, identity gate behavior, context policies, and derived summaries. Those are rules about content, not ownership of the content.

## 3. Top-Level Structure

```text
ai-workroot/
  START_HERE_FOR_HUMANS.md
  AGENTS.md
  CLAUDE.md
  README.md
  PROJECT_BRIEF.md
  AUTHOR.md
  LICENSE
  NOTICE
  TRADEMARKS.md
  CONTRIBUTING.md
  DCO.md
  ROADMAP.md

  space/
    profile/
    work/
    mind/
    inbox/
    files/

  .workroot/
    kernel/
    extensions/
    runtime/

  docs/
  assets/
  scripts/
  tests/
  .github/
```

## 4. Layer Responsibilities

### `space/`

The visible user-owned, protocol-governed workspace.

Ordinary users may add their own folders inside `space/`. The kernel should not treat user-created folders as errors.

However, the protocol anchor folders under `space/` must remain stable:

```text
space/profile/
space/work/
space/mind/
space/inbox/
space/files/
```

Users own the content in these folders, but agents and tools rely on their meanings.

User-added folders are free-form. When their content should become durable identity, work, knowledge, memory, source material, or handoff, agents should connect it back to the protocol anchors through links, summaries, registries, or preservation actions.

### `space/profile/`

Defines who this Workroot represents.

This is the first required setup layer. A Workroot can start with a small identity, but it should not start durable formal work without one.

`space/profile/` is the source of truth for identity content.

The kernel defines the identity gate and minimum identity contract. It does not own the user's actual identity content.

Derived identity summaries may exist under `.workroot/runtime/` for context efficiency, but they must be rebuildable from `space/profile/`.

The subject can be:

- a person
- a team
- a role
- a project
- an organization

For a person, identity includes profile, roles, values, preferences, and current life/work context.

For a team, identity includes mission, shared roles, standards, and collaboration preferences.

### `space/work/`

The user-visible work surface.

It contains summaries, final outputs, reports, and artifacts that ordinary users should naturally inspect.

Internal task mechanics belong under `.workroot/runtime/work/`.

### `space/mind/`

The long-term externalized mind of the subject.

It is not only a knowledge base. It includes memory, knowledge, principles, decisions, patterns, reflections, invalidated beliefs, released past context, and tombstones.

`space/mind/knowledge/` may be freely organized into subject-specific domains as the person or team grows. The protocol requires discoverability, links, and index discipline, not one fixed taxonomy for everyone.

Recommended substructure:

```text
space/mind/
  memory/
  knowledge/
  principles/
  decisions/
  patterns/
  reflections/
  invalidated/
  released/
```

### `space/inbox/`

The low-friction entry point for unclassified material.

Users can drop thoughts, questions, files, links, or rough ideas here. Agents can later classify them into work, memory, knowledge, files, or decisions.

### `space/files/`

User-provided source materials and references.

Files are evidence or source material. They are not automatically stable knowledge.

### `.workroot/kernel/`

The stable operating law.

It owns philosophy, product rules, protocols, contracts, interfaces, agent rules, configuration, schemas, and kernel scripts.

Ordinary users should not need to manage it.

### `.workroot/extensions/`

The replaceable capability layer.

It contains optional capabilities, skills, MCP bridges, agent adapters, storage drivers, retrieval drivers, and import/export drivers.

Extensions may add power, but they must not redefine kernel semantics.

User space and extensions should remain open-ended. The kernel protects continuity, lifecycle meaning, and source-of-truth rules; it should not constrain the concrete domains, professions, projects, or personal structures that a Workroot can support.

### `.workroot/runtime/`

System-managed runtime state.

It contains continuation context, internal work records, indexes, optional generated data stores, caches, and logs.

Runtime stores are rebuildable accelerators or operational state, not the only source of durable truth.

## 5. Mind Model

`space/mind/` is the most important human continuity abstraction.

### Memory

Memory records what happened.

It is episodic and contextual:

- experiences
- important moments
- task outcomes
- conversations
- emotional traces
- turning points
- evidence of growth

Memory answers:

> What happened?

### Knowledge

Knowledge records what has been learned.

It is generalized and reusable:

- stable facts
- concepts
- methods
- domain understanding
- reusable conclusions
- source maps
- explanatory models

Knowledge answers:

> What do I understand now and reuse later?

### Principles

Principles are rules, values, boundaries, and operating commitments.

Knowledge describes. Principles prescribe.

### Decisions

Decisions record important choices and their reasons.

They preserve why a path was chosen, what alternatives existed, and whether the choice was later validated or revised.

### Patterns

Patterns record repeated behaviors, recurring problems, strengths, constraints, and successful approaches.

They help the subject recognize themselves over time.

### Reflections

Reflections are reviews and deeper thinking.

They convert raw experience into self-understanding.

### Invalidated

Invalidated records preserve what should no longer be believed or reused.

This prevents old assumptions from returning silently.

### Released

Released records preserve the fact that something has been consciously released from active recall.

This is for painful memories, past mistakes, or old contexts where the useful lesson has already been extracted and the subject chooses not to keep carrying the raw experience forward.

Released does not mean forced deletion. It means normal agents should not resurface the material unless the user asks, or unless there is a serious safety, legal, or integrity reason.

A released item can also become a tombstone: a minimal memorial marker kept for intentional remembrance, mourning, or closure. Tombstones should not hold full painful detail, and they can be deleted later by explicit user choice.

## 6. Work Model

Work has two surfaces:

```text
space/work/                user-visible summaries, reports, outputs
.workroot/runtime/work/    internal task state and mechanics
```

For formal work, internal task records may include:

```text
task.json
brief.md
decisions.md
todo.md
scratch.md
index.md
outputs/
handoff.md
```

Responsibilities:

- `task.json`: identity, goal, scope, owner, status
- `brief.md`: current effective state
- `decisions.md`: decisions, corrections, invalidated assumptions
- `todo.md`: remaining work only
- `scratch.md`: optional working scratchpad, not startup context
- `index.md`: task-local index of outputs, references, decisions, and promoted entries
- `outputs/`: task-local working outputs before user-visible material is copied or summarized into `space/work/`
- `handoff.md`: continuation card for future sessions

Upgrade path:

```text
casual question -> quick answer
quick answer -> saved result if useful
goal-oriented work -> internal task record
internal task result -> user-visible output
reusable result -> knowledge
meaningful experience -> memory
important choice -> decision
wrong assumption -> invalidated
lesson learned from pain -> released
repeated workflow -> extension capability
```

## 7. Multi-Level Indexing

AI context organization depends on indexes.

AI Workroot uses indexes not only as technical tables, but as the nervous system of the workspace.

Recommended levels:

```text
L0 Boot Context
  AGENTS.md, START_HERE_FOR_HUMANS.md, .workroot/kernel/boot/boot.md

L1 Active Context
  .workroot/runtime/context/current.md, .workroot/runtime/context/handoff.md

L2 Kernel Index
  .workroot/kernel/contracts/, .workroot/kernel/schemas/

L3 Work And Mind Index
  .workroot/runtime/index/*.csv

L4 Extension Index
  .workroot/extensions/capability_registry.csv and extension manifests

L5 Acceleration Index
  optional SQLite, DuckDB, vector index, graph index
```

Important rule:

> Indexes accelerate traversal. They do not replace the file-based source of truth.

See `docs/scaling-and-longevity.md` for long-term context, lifecycle, indexing, and storage rules.

## 8. Knowledge Network

Human memory is not a flat folder tree. It is a network.

AI Workroot should gradually connect:

- profile
- roles
- work
- memories
- knowledge
- decisions
- artifacts
- principles
- files
- capabilities
- invalidated understandings

The public seed can use Markdown, JSON, and CSV. Future versions may add SQLite, DuckDB, vector retrieval, or graph indexes.

The conceptual model remains:

> files are the body, indexes are the nervous system, Mind is the growing externalized cognition.

## 9. Optional Local Databases

Databases are optional accelerators.

They should be:

- local-first
- cross-platform
- disposable
- rebuildable from files
- documented by manifest files
- read-only by default where practical

Recommended future categories:

- SQLite: default cross-platform local index/store
- DuckDB: optional local analytical/process store for OLAP-style task or role analysis
- vector index: optional semantic retrieval accelerator
- graph index: optional relationship traversal accelerator

AI Workroot should support macOS, Windows, and Linux. Installation may differ by operating system; agents can help install tools according to this protocol.

For current practice, SQLite is the recommended first database for point lookup, local indexes, and lightweight state because it is local, cross-platform, and easy to rebuild from file-based registries.

DuckDB is appropriate when a concrete Workroot needs local analytical work, such as tabular exploration, larger joins, profiling, or repeatable OLAP-style task analysis.

Vector and graph indexes should remain future extensions unless a concrete Workroot needs them.

## 10. Core Skill Priority

The Workroot operating protocol is the core skill of AI Workroot.

It defines the root thinking pattern:

- human-centered continuity
- layered memory
- task-to-result-to-knowledge flow
- multi-level indexing
- tool-agnostic collaboration
- preservation of values, decisions, and growth

Other skills are allowed, but they operate inside the Workroot protocol.

Priority rule:

```text
User's latest explicit instruction
> AI Workroot operating protocol
> this Workroot's profile, mind, and governance
> current task brief and decisions
> role/domain/tool skills
> agent default behavior
```

## 11. Export And Portability

The user's past belongs to the user.

AI Workroot should support:

- backup
- export
- import into another agent or system
- continued use with different models

The project should not trap users. It should help them own their continuity.
