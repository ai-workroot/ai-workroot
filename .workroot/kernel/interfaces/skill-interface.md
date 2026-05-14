# Skill Interface

Skills are agent-compatible instruction packages.

A skill may contain instructions, scripts, references, and assets. It must operate inside the Workroot protocol and must not become a second source of truth.

Skills should declare when they apply, what they may read, what they may write, what scripts they may run, what outputs they may produce, and what privacy rules apply.

Default rule:

```text
Skills are never startup context unless the boot contract explicitly says so.
```
