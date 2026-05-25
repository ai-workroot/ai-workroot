"""Build-context application command."""

from __future__ import annotations

from pathlib import Path

from ai_workroot.context.builder import ContextRequest, build_context_package
from ai_workroot.state.environment import load_context_control_config
from ai_workroot.state.layout import resolve_ai_workroot_home


def build_context(
    *,
    agent: str,
    cwd: Path | str = ".",
    query: str = "",
    mode: str = "standard",
    target_tokens: int | None = None,
    hard_token_limit: int | None = None,
    debug: bool = False,
) -> str:
    config = load_context_control_config(resolve_ai_workroot_home())
    resolved_target_tokens = target_tokens if target_tokens is not None else config.default_target_tokens
    resolved_hard_token_limit = hard_token_limit if hard_token_limit is not None else config.default_hard_token_limit
    budget_source = "cli" if target_tokens is not None or hard_token_limit is not None else "config"
    if (
        resolved_target_tokens <= 0
        or resolved_hard_token_limit <= 0
        or resolved_target_tokens > resolved_hard_token_limit
    ):
        raise ValueError("invalid context token budget")
    return build_context_package(
        ContextRequest(
            agent=agent,
            cwd=Path(cwd),
            query=query,
            mode=mode,
            target_tokens=resolved_target_tokens,
            hard_token_limit=resolved_hard_token_limit,
            debug=debug,
            budget_source=budget_source,
        )
    )


__all__ = ["ContextRequest", "build_context", "build_context_package"]
