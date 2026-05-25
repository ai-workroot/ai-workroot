"""Template contracts."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TemplateRenderer(Protocol):
    def render(self, template_name: str, variables: dict[str, str]) -> str:
        """Render a named template with string variables."""
