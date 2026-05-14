# Capability Interface

Capabilities define repeatable workflows.

They may add templates, scripts, checklists, manifests, domain registries, and role guidance under `.workroot/extensions/capabilities/`.

They must not redefine identity, work lifecycle, memory lifecycle, knowledge promotion, release semantics, source-of-truth rules, kernel contracts, or compatibility semantics.

Capabilities should declare read scope, write scope, privacy level, required tools, optional tools, generated stores, and rebuild behavior when they become non-trivial.

Capability details are not startup context unless the boot contract explicitly says so.
