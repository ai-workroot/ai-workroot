"""Minimal Context Control runtime flow."""

from __future__ import annotations

from dataclasses import dataclass
import time
from pathlib import Path

from ai_workroot.runtime.registry import find_workroot_by_cwd


DEFAULT_TARGET_TOKENS = 1200
DEFAULT_HARD_TOKEN_LIMIT = 2400


@dataclass(frozen=True)
class ContextRequest:
    agent: str
    cwd: Path | str = "."
    query: str = ""
    mode: str = "standard"
    target_tokens: int = DEFAULT_TARGET_TOKENS
    hard_token_limit: int = DEFAULT_HARD_TOKEN_LIMIT
    debug: bool = False


def build_context_package(
    request: ContextRequest,
    *,
    ai_workroot_home: Path | str | None = None,
) -> str:
    started = time.perf_counter()
    record = find_workroot_by_cwd(request.cwd, ai_workroot_home=ai_workroot_home)
    selected = _discover_user_assets(Path(record["userDirectory"]))
    rendered_body = "\n".join(f"- {path}" for path in selected) or "- No user assets selected yet."
    token_usage = _estimate_tokens(rendered_body + request.query)
    latency_ms = int((time.perf_counter() - started) * 1000)

    lines = [
        "# AI Workroot Context Package",
        "",
        f"Workroot: {record['name']} ({record['workrootId']})",
        f"Agent: {request.agent}",
        f"Mode: {request.mode}",
        "Confidence: 0.60",
        f"LatencyMs: {latency_ms}",
        f"TokenUsage: {token_usage}/{request.hard_token_limit}",
    ]
    if request.query:
        lines.append(f"Query: {request.query}")
    lines.extend(
        [
            "",
            "## Selected Context",
            rendered_body,
        ]
    )
    if request.debug:
        lines.extend(
            [
                "",
                "## Debug Trace",
                "candidateSources: user-assets, registry",
                "filters: safety=default lifecycle=active",
                "scoring: recency=0 explicit=0 relationship=0",
                f"timing: totalMs={latency_ms}",
                f"tokenUsage: estimated={token_usage} target={request.target_tokens} hard={request.hard_token_limit}",
            ]
        )
    return "\n".join(lines) + "\n"


def _discover_user_assets(user_directory: Path) -> list[str]:
    if not user_directory.exists():
        return []
    assets: list[str] = []
    for path in sorted(user_directory.iterdir()):
        if path.name in {"AGENTS.md", "CLAUDE.md"} or path.name.startswith("."):
            continue
        if path.is_file():
            assets.append(path.name)
    return assets[:10]


def _estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)
