#!/usr/bin/env python3
"""Native Agent Entry managed blocks for AI Workroot."""

from __future__ import annotations

import re
from pathlib import Path


BEGIN = "<!-- AI_WORKROOT_BEGIN -->"
END = "<!-- AI_WORKROOT_END -->"


class NativeAgentEntryError(ValueError):
    pass


FORBIDDEN_PATTERNS = [
    re.compile(r"/Users/[^/\s]+/\.ai-workroot/workroots"),
    re.compile(r"\\Users\\[^\\\s]+\\AppData\\Local\\AIWorkroot\\workroots", re.IGNORECASE),
    re.compile(r"\.ai-workroot[/\\]workroots"),
    re.compile(r"context/debug"),
    re.compile(r"handoffs/"),
    re.compile(r"logs/"),
    re.compile(r"indexes/"),
]


def validate_entry_content(text: str) -> None:
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(text):
            raise NativeAgentEntryError(f"Native Agent Entry contains forbidden managed-state detail: {pattern.pattern}")


def managed_block(body: str) -> str:
    text = f"{BEGIN}\n{body.strip()}\n{END}\n"
    validate_entry_content(text)
    return text


def codex_block() -> str:
    return managed_block(
        """
# AI Workroot Agent Entry

Before answering, editing, creating files, or making decisions in this directory, obtain the current Workroot context:

```bash
workroot context --agent codex --cwd .
```

Use the returned Context Package for current focus, active task, recent decisions, handoffs, artifact guidance, and write-routing rules.

Do not write Workroot managed state into this directory.

If the context command fails, answer only low-risk questions from explicit user instructions and ask the user to run `workroot doctor` before major changes.
"""
    )


def claude_block() -> str:
    return managed_block(
        """
@AGENTS.md

## Claude Code Entry

Before answering, editing, creating files, or making decisions in this directory, obtain the current Workroot context:

```bash
workroot context --agent claude --cwd .
```

If the context command fails, answer only low-risk questions from explicit user instructions and ask the user to run `workroot doctor` before major changes.
"""
    )


def replace_existing_block(text: str, block: str) -> str:
    begin_count = text.count(BEGIN)
    end_count = text.count(END)
    if begin_count != end_count:
        raise NativeAgentEntryError("malformed AI Workroot managed block markers")
    if begin_count == 0:
        separator = "\n\n" if text.strip() else ""
        return text.rstrip() + separator + block
    if begin_count > 1:
        raise NativeAgentEntryError("multiple AI Workroot managed blocks are not supported")
    before, rest = text.split(BEGIN, 1)
    _, after = rest.split(END, 1)
    return before.rstrip() + "\n\n" + block + after.lstrip("\n")


def apply_managed_block(path: Path, block: str) -> None:
    validate_entry_content(block)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    updated = replace_existing_block(text, block)
    validate_entry_content(updated)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated, encoding="utf-8")
