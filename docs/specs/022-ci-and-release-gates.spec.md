# Spec 022 — CI and Release Gates

Status: accepted
Applies to: 0.9.530

## Required CI jobs

At minimum:

```text
Python compile
Unit tests
Integration tests
Smoke tests
Release validation
Git diff check
Install script syntax check
```

Example commands:

```bash
python3 -m py_compile $(find src scripts -name "*.py")
python3 -m unittest discover -s tests -v
python3 scripts/validate_kernel.py --release  # baseline only until Clean Workroot validator replaces it
git diff --check
bash -n install/unix/install.sh
```

PowerShell parse should be included if available. If not, document limitation.

Final release CI must include a Clean Workroot release validator. The old kernel validator cannot be the sole final release gate unless rewritten for the 0.9.530 architecture.

## Release gate

Before tag:

1. Final report complete.
2. Acceptance checklist complete.
3. Negative tests complete.
4. Smoke tests complete.
5. Known limitations documented.
6. Human review approves tag.
7. Clean Workroot release validator output is included.

## No automatic tag

Codex must not tag unless explicitly instructed after review.
