# Spec: Project Structure and Naming

## Status

Draft

## Priority

P0

## Background

AI Workroot 0.9.529 changes the product foundation from a visible protocol seed toward a personal, local-first product with a clean user-selected directory and managed state outside that directory. This Spec defines the naming, product boundaries, and structure terms that all other 0.9.529 Specs must use.

It exists to prevent old terminology, old public-seed assumptions, or OS-specific meanings of "root" from leaking into the implementation.

## Goals

- Use "AI Workroot", "Workroot", or "Work Root" consistently.
- Position the product as a personal, local-first AI Workroot for individuals.
- Define the core directory concepts used by implementation Specs.
- Separate consumer Clean Mode from developer Bootstrap Mode.
- Preserve the rule that global state owns indexes and navigation, not Workroot knowledge.

## Non-goals

- This Spec does not implement the CLI, installer, bootstrap workflow, or storage layout.
- This Spec does not rewrite all existing documentation.
- This Spec does not define a team collaboration product.
- This Spec does not define hosted services, cloud sync, or remote retrieval.

## Scope

### Included

- Product naming rules.
- User directory, managed state directory, global system space, and Native Agent Entry terminology.
- Mode naming for Clean Mode and developer-only Bootstrap Mode.
- Documentation and code naming conventions for 0.9.529 work.

### Excluded

- Concrete file creation behavior, covered by `002-clean-mode-installation.spec.md`.
- Managed state layout details, covered by `003-managed-state-layout.spec.md`.
- Bootstrap execution details, covered by `004-bootstrap-process.spec.md`.
- Release gates, covered by `014-release-and-test-gates.spec.md`.

## Dependencies

- Core project decisions: Clean Mode; managed state outside the user directory; controlled bootstrap; high-quality Context Guide; Materialized Context Candidates; local-first explainable retrieval without a P0 vector dependency; debug traces; branch-and-review Git workflow; English-first docs and comments.
- Architecture design: `AI Workroot 0.9.529 Architecture Design`.
- Existing project docs under `docs/`.
- Core decision: personal AI Workroot, not team collaboration.
- Core decision: use Workroot or Work Root consistently.

## Requirements

### Functional Requirements

FR-001: Product-facing and implementation-facing documents for 0.9.529 must use "AI Workroot", "Workroot", or "Work Root" as the product category.

FR-002: 0.9.529 implementation Specs must not position the product as an "AI Workspace".

FR-003: Implementation Specs must avoid standalone "root" as an internal concept name where it can be confused with OS directory, superuser, or permission concepts.

FR-004: Specs must define "user directory" as the user-selected asset space.

FR-005: Specs must define "managed state directory" as AI Workroot-owned state outside the user directory by default.

FR-006: Specs must define "global system space" as the user-level AI Workroot home that owns registry, global indexes, user preferences, and global cache.

FR-007: Specs must define "Native Agent Entry files" as optional agent-native entry files in the user directory, not as Workroot managed state.

FR-008: Specs must distinguish consumer Clean Mode from developer-only Bootstrap Mode.

### Non-functional Requirements

NFR-001: Naming must be clear for international English-first users.

NFR-002: Naming must reduce ambiguity with OS path and permission terminology.

NFR-003: Documentation must remain readable without requiring users to understand internal state architecture.

NFR-004: The naming model must remain compatible with macOS, Linux, and Windows.

## Proposed Design

### Concepts

- Workroot: The personal AI work foundation that connects user assets, managed state, context, decisions, tasks, and retrieval.
- User directory: A directory selected by the user that stores user assets and ordinary project files.
- Managed state directory: A per-Workroot system directory under AI Workroot home that stores continuity state, indexes, context packages, debug traces, graph data, and caches.
- Global system space: The AI Workroot home, resolved by `AI_WORKROOT_HOME` or OS defaults.
- Clean Mode: The default consumer mode where managed state stays outside the user directory.
- Bootstrap Mode: A developer-only workflow for using AI Workroot to develop AI Workroot.
- Native Agent Entry files: Optional `AGENTS.md` and `CLAUDE.md` entry files that tell agents how to request context.

### Data Model

This Spec defines naming and concept contracts only. Concrete data models are defined in downstream Specs.

Minimum concept names:

```json
{
  "product_name": "AI Workroot",
  "workroot_id": "string",
  "mode": "clean | bootstrap-dev",
  "user_directory": "path",
  "managed_state_directory": "path",
  "global_system_space": "path"
}
```

### File Layout

This Spec does not create files. It reserves terminology used by these layouts:

```text
User directory
  user assets
  optional Native Agent Entry files

AI Workroot home
  registry/
  global-index/
  global-cache/
  workroots/<workrootId>/
```

No Workroot control state is allowed inside the user-selected directory by default.

### CLI / API

CLI help, command descriptions, and error messages must use these names:

```text
workroot init
workroot context
workroot doctor
workroot bootstrap-dev
```

Avoid command or option names that use standalone "root" for Workroot concepts.

### Runtime Behavior

Runtime behavior is defined by downstream Specs. Runtime messages must preserve the directory boundary:

- user directory means user assets;
- managed state directory means AI Workroot state;
- global system space means user-level AI Workroot state.

### Error Handling

Errors must name the violated boundary plainly. For example:

```text
Clean Mode violation: managed state would be written inside the user directory.
```

Error messages must not ask ordinary users to understand internal implementation concepts unless the command is developer-facing.

### Security / Privacy

Naming must reinforce that user assets are user-owned and managed state is local-first. Product copy must not imply cloud ownership, hosted storage, or team-visible sharing by default.

### Compatibility

Existing docs may contain older public-seed language. 0.9.529 Specs should treat those phrases as legacy context and should not copy them into new implementation docs, CLI help, or user flows.

## Acceptance Criteria

AC-001:
Given a 0.9.529 Spec
When it describes the product category
Then it uses "AI Workroot", "Workroot", or "Work Root" rather than "AI Workspace".

AC-002:
Given implementation-facing names for directories or state
When a concept could be confused with OS root
Then the name uses "Workroot" or a more specific term instead of standalone "root".

AC-003:
Given a Clean Mode flow
When it describes storage
Then it clearly separates user directory and managed state directory.

AC-004:
Given developer bootstrap documentation
When it describes Bootstrap Mode
Then it identifies it as developer-only and not a consumer-facing mode.

## Test Plan

### Unit Tests

- Add text lint checks for forbidden product-positioning phrases in new 0.9.529 docs.
- Add CLI help snapshot tests to verify approved naming.

### Integration Tests

- Run a documentation scan over `docs/specs/` to ensure new Specs use approved terminology.
- Run CLI help and confirm command descriptions use Workroot terminology.

### Manual Verification

- Review new Specs for user-facing clarity.
- Review README and core docs during implementation to identify legacy wording that needs later updates.

## Migration / Rollback

Migration is documentation and naming-only for this Spec. Rollback means reverting the wording changes made by downstream implementation work.

## Observability / Debugging

Doctor should eventually report legacy naming only when it affects product behavior or release readiness. It should not block local development merely because older historical docs contain legacy terms.

## Task Breakdown

T1: Add naming constants and glossary
- Change: Define canonical terms for Workroot, user directory, managed state directory, global system space, Clean Mode, Bootstrap Mode, and Native Agent Entry.
- Files likely affected: `docs/specs/`, future CLI help docs.
- Verification: Documentation scan confirms canonical terms exist.

T2: Add documentation lint rules
- Change: Add release-check text checks for product-positioning phrases and standalone ambiguous concept names.
- Files likely affected: `scripts/validate_kernel.py`, `tests/test_architecture_contracts.py`.
- Verification: Run targeted docs lint tests.

T3: Update CLI copy during implementation
- Change: Ensure CLI help and errors use canonical naming.
- Files likely affected: `scripts/workroot_cli.py`, future CLI modules.
- Verification: CLI help snapshot tests pass.

## Risks

- Existing docs contain older public-seed language and may require staged updates.
- Overly aggressive linting could block legitimate historical references or conflict reports.
- The product name may be translated inconsistently if future localization is added.

## Open Questions

None.
