"""Cross-capability configuration views."""

from __future__ import annotations

from pathlib import Path

from ai_workroot.capabilities.assets.rules import compact_output_rules


def compact_asset_output_rules(state_directory: Path | str, *, limit: int = 5) -> list[dict[str, str]]:
    return compact_output_rules(Path(state_directory), limit=limit)
