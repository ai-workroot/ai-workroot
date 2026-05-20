# AI Workroot 0.9.530 Specs

Status: accepted source of truth for `feat/0.9.530-clean-workroot-domain-reset`.

AI Workroot 0.9.530 is a Clean Workroot architecture reset, not a normal bugfix release. The active architecture is Clean Workroot. Public Seed is historical and must not remain the active root layout after the replacement architecture is working.

## Reading Order

1. `001-project-structure-and-naming.spec.md`
2. `002-clean-workroot-installation.spec.md`
3. `003-workroot-environment-managed-state.spec.md`
4. `004-bootstrap-dev-dogfood.spec.md`
5. `005-core-model.spec.md`
6. `006-asset-model.spec.md`
7. `007-release-control.spec.md`
8. `008-relationship-network.spec.md`
9. `009-retrieval-index-control.spec.md`
10. `010-context-control.spec.md`
11. `011-agent-interface-native-entry.spec.md`
12. `012-system-health-doctor-migration.spec.md`
13. `013-storage-sqlite-schema.spec.md`
14. `014-cli-user-flows.spec.md`
15. `015-installation-scripts.spec.md`
16. `016-source-layout-migration.spec.md`
17. `017-release-validation.spec.md`
18. `018-codex-execution-plan.spec.md`
19. `019-full-test-and-migration-plan.spec.md`
20. `020-documentation-rewrite.spec.md`
21. `021-codex-checkpoint-protocol.spec.md`
22. `022-ci-and-release-gates.spec.md`

## Required Companion Docs

- `docs/architecture/`
- `docs/adr/`
- `docs/validation/`
- `docs/dev/0.9.530/final-architect-review-clarifications.md`
- `docs/dev/0.9.530/matrix/legacy-capability-preservation-matrix.md`
- `docs/dev/0.9.530/execution/001-implementation-order-and-checkpoints.md`

## Execution Rule

Build the replacement architecture first, then quarantine the old Public Seed active root.

Do not begin by deleting or moving root `space/`, `.workroot/`, `AGENTS.md`, or `CLAUDE.md`. Quarantine only after packaged templates, bootstrap-dev, runtime entry points, tests, docs, and doctor checks can replace the old path.

## Retired 0.9.529 Specs

The 0.9.529 specs are preserved under:

```text
docs/history/0.9.529/specs/
```

They remain useful implementation history, but they are not the current source of truth for 0.9.530.
