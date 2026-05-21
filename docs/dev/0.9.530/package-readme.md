# AI Workroot 0.9.530 Final Codex Implementation Package

> This is an imported package README retained for traceability.
> If this file conflicts with `docs/dev/0.9.530/final-architect-review-clarifications.md`, `docs/specs/`, `docs/architecture/`, `docs/adr/`, or `docs/history/0.9.530/plans/2026-05-20-0530-clean-workroot-domain-reset-plan.md`, the later clarified documents win.

This package is the final source of truth for the 0.9.530 Clean Workroot architecture reset.

It combines:

- the strategic domain model clarified through discussion;
- the lightweight engineering architecture to implement it;
- detailed specs;
- migration plans;
- documentation rewrite plans;
- testing and negative test plans;
- Codex execution order;
- release validation gates.

Codex must not redesign the architecture. Codex should implement the plan, report deviations, and ask for review when a required behavior cannot be implemented safely.

Recommended branch:

```text
feat/0.9.530-clean-workroot-domain-reset
```

Primary all-in-one file:

```text
FINAL_ALL_IN_ONE.md
```
