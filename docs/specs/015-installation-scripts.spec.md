# Spec 015 — Installation Scripts

Status: accepted  
Target: 0.9.530

## Purpose

Move user install scripts out of generic `scripts/` and separate user install from developer tooling.

## Target layout

```text
install/
  README.md
  unix/
    install.sh
  windows/
    install.ps1

scripts/
  dev/
    bootstrap-dev.sh
    bootstrap-dev.ps1
    validate-release.sh
```

## Rules

- `install/` is user-facing.
- `scripts/dev/` is developer-facing.
- Product core logic must not live in shell scripts.
- Install scripts should call packaged CLI or install package wrapper.

## Unix installer

Covers macOS/Linux for now.

Do not split macOS/Linux until behavior truly diverges.

## Windows installer

PowerShell script under `install/windows/install.ps1`.

## Acceptance

- old `scripts/install.sh` and `scripts/install.ps1` are wrappers or moved.
- docs point to new install paths.
- shell parse passes for unix installer.
- PowerShell parse/documented validation included where possible.
