# AI Workroot Specs

Specs are stable implementation contracts. They are not Agent execution plans
or process scratchpads.

For documentation rules, read `docs/DOCUMENTATION_POLICY.md`.

## Current Reading Order

For the current accepted architecture and protocol line, read:

1. `docs/workroot-system-design.md`
2. `docs/architecture.md`
3. `docs/architecture/010-runtime-layering.md`
4. `011-agent-interface-native-entry.spec.md`
5. `042-agent-protocol-context-strategy.spec.md`
6. `043-continuity-owner-and-evidence-hardening.spec.md`
7. `044-sqlite-schema-migrations.spec.md`
8. `045-sync-owner-binding-and-lease-guard.spec.md`
9. `docs/releases/0.9.531.md`

## Current Specs

These specs describe behavior that remains active in the current Clean
Workroot implementation line:

- `001-project-structure-and-naming.spec.md`
- `002-clean-workroot-installation.spec.md`
- `003-workroot-environment-managed-state.spec.md`
- `004-bootstrap-dev-dogfood.spec.md`
- `005-core-model.spec.md`
- `006-asset-model.spec.md`
- `007-release-control.spec.md`
- `008-relationship-network.spec.md`
- `009-retrieval-index-control.spec.md`
- `010-context-control.spec.md`
- `011-agent-interface-native-entry.spec.md`
- `013-storage-sqlite-schema.spec.md`
- `014-cli-user-flows.spec.md`
- `017-release-validation.spec.md`
- `022-ci-and-release-gates.spec.md`
- `035-workroot-environment-config-contract.spec.md`
- `036-e2e-sandbox-and-destructive-operation-safety.spec.md`
- `037-release-derived-index-safety-hardening.spec.md`
- `038-active-context-control-parity-hardening.spec.md`
- `041-runnable-legacy-compat-removal.spec.md`
- `042-agent-protocol-context-strategy.spec.md`
- `043-continuity-owner-and-evidence-hardening.spec.md`
- `044-sqlite-schema-migrations.spec.md`
- `045-sync-owner-binding-and-lease-guard.spec.md`

When an older spec conflicts with the current architecture docs or Spec 042,
the newer current document wins.

## Historical Or Transitional Specs

The remaining 0.9.530 specs are implementation history for the Clean Workroot
reset and migration:

- `012-system-health-doctor-migration.spec.md`
- `015-installation-scripts.spec.md`
- `016-source-layout-migration.spec.md`
- `018-codex-execution-plan.spec.md`
- `019-full-test-and-migration-plan.spec.md`
- `020-documentation-rewrite.spec.md`
- `021-codex-checkpoint-protocol.spec.md`
- `023-active-package-cli-and-legacy-isolation.spec.md`
- `024-work-and-asset-runtime-migration.spec.md`
- `025-storage-and-migrations-migration.spec.md`
- `026-retrieval-indexing-and-context-control-migration.spec.md`
- `027-release-relationship-and-safety-migration.spec.md`
- `028-system-health-validation-and-checkbot.spec.md`
- `029-install-dev-scripts-and-wrappers.spec.md`
- `030-test-suite-and-public-seed-quarantine.spec.md`
- `031-compatibility-preserving-script-migration.spec.md`
- `032-part2-capability-parity-small-specs.spec.md`
- `033-time-and-global-index-parity.spec.md`
- `034-end-to-end-persona-smoke-testing.spec.md`
- `039-publication-authoring-index-doctor-hardening.spec.md`
- `040-0530-focused-hardening.spec.md`

These documents remain useful for migration reasoning, but they are not the
first source of truth for current behavior.

## Retired 0.9.529 Specs

The 0.9.529 specs are preserved under:

```text
docs/history/0.9.529/specs/
```

They are not current implementation contracts.
