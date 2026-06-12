"""Native Agent Entry rendering and managed-block updates."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
import re


MANAGED_BLOCK_BEGIN = "<!-- AI_WORKROOT_BEGIN -->"
MANAGED_BLOCK_END = "<!-- AI_WORKROOT_END -->"
BEGIN = MANAGED_BLOCK_BEGIN
END = MANAGED_BLOCK_END
TEMPLATE_PACKAGE = "ai_workroot.entrypoints.native_agent.templates"
SAFE_AGENT_RE = re.compile(r"^[a-z0-9._-]{1,64}$")


class NativeAgentEntryError(ValueError):
    """Raised when a Native Agent Entry template or block is unsafe."""


def render_native_agent_entry(agent: str) -> str:
    normalized_agent = agent.strip().lower()
    _validate_agent_descriptor(normalized_agent)
    template_name = _template_name(normalized_agent)
    template = resources.files(TEMPLATE_PACKAGE).joinpath(template_name).read_text(encoding="utf-8")
    rendered = template.replace("{{agent}}", normalized_agent)
    validate_managed_block(rendered)
    return rendered


def codex_block() -> str:
    return render_native_agent_entry("codex")


def claude_block() -> str:
    return render_native_agent_entry("claude")


def sync_native_agent_entry(path: Path, agent: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    block = render_native_agent_entry(agent)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(_replace_managed_block(existing, block), encoding="utf-8")


def apply_managed_block(path: Path, block: str) -> None:
    validate_entry_content(block)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(_replace_managed_block(existing, block), encoding="utf-8")


def validate_entry_content(text: str) -> None:
    if MANAGED_BLOCK_BEGIN in text or MANAGED_BLOCK_END in text:
        validate_managed_blocks(text)
        return
    _validate_native_entry_text(text)


def validate_managed_blocks(text: str) -> None:
    position = 0
    while MANAGED_BLOCK_BEGIN in text[position:]:
        start = text.index(MANAGED_BLOCK_BEGIN, position)
        if MANAGED_BLOCK_END not in text[start:]:
            raise NativeAgentEntryError("existing Native Agent Entry has invalid AI Workroot managed block markers")
        end = text.index(MANAGED_BLOCK_END, start) + len(MANAGED_BLOCK_END)
        _validate_native_entry_text(text[start:end])
        position = end


def validate_managed_block(block: str) -> None:
    if block.count(MANAGED_BLOCK_BEGIN) != 1 or block.count(MANAGED_BLOCK_END) != 1:
        raise NativeAgentEntryError("Native Agent Entry must contain exactly one AI Workroot managed block")
    managed = _managed_block_body(block)
    _validate_native_entry_text(managed)


def _validate_native_entry_text(managed: str) -> None:
    forbidden_terms = (
        "AI_WORKROOT_HOME",
        "workroot_id",
        ".ai-workroot/workroots",
        "logs",
        "indexes",
        "handoffs",
        "context package history",
    )
    for term in forbidden_terms:
        if term.lower() in managed.lower():
            raise NativeAgentEntryError(f"Native Agent Entry managed block contains forbidden term: {term}")
    for line in managed.splitlines():
        if line.startswith("/") or " /Users/" in line or " C:\\" in line:
            raise NativeAgentEntryError("Native Agent Entry managed block must not contain absolute local paths")


def _template_name(agent: str) -> str:
    if agent == "codex":
        return "AGENTS.md.template"
    if agent == "claude":
        return "CLAUDE.md.template"
    return "GENERIC.md.template"


def _validate_agent_descriptor(agent: str) -> None:
    if not SAFE_AGENT_RE.fullmatch(agent):
        raise NativeAgentEntryError("Native Agent Entry agent descriptor must match [a-z0-9._-]{1,64}")


def _managed_block_body(text: str) -> str:
    start = text.index(MANAGED_BLOCK_BEGIN) + len(MANAGED_BLOCK_BEGIN)
    end = text.index(MANAGED_BLOCK_END)
    if start > end:
        raise NativeAgentEntryError("Native Agent Entry managed block markers are out of order")
    return text[start:end]


def _replace_managed_block(existing: str, block: str) -> str:
    if MANAGED_BLOCK_BEGIN not in existing and MANAGED_BLOCK_END not in existing:
        prefix = existing.rstrip()
        return f"{prefix}\n\n{block.rstrip()}\n" if prefix else f"{block.rstrip()}\n"
    if existing.count(MANAGED_BLOCK_BEGIN) != 1 or existing.count(MANAGED_BLOCK_END) != 1:
        raise NativeAgentEntryError("existing Native Agent Entry has invalid AI Workroot managed block markers")
    start = existing.index(MANAGED_BLOCK_BEGIN)
    end = existing.index(MANAGED_BLOCK_END) + len(MANAGED_BLOCK_END)
    updated = existing[:start].rstrip() + "\n\n" + block.rstrip() + "\n" + existing[end:].lstrip()
    return updated if updated.endswith("\n") else updated + "\n"
