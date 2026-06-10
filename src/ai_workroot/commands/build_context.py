"""Build-context application command."""

from __future__ import annotations

from pathlib import Path
import uuid

from ai_workroot.capabilities.context.builder import ContextRequest as _ContextRequest
from ai_workroot.capabilities.context.builder import build_context_package as _build_context_package
from ai_workroot.protocol.controller import startup_context
from ai_workroot.protocol.model import PROTOCOL_VERSION
from ai_workroot.protocol.packet import render_private_packet_markdown
from ai_workroot.protocol.work_signal import WorkSignal
from ai_workroot.state.environment import load_context_control_config
from ai_workroot.state.layout import resolve_ai_workroot_home


def build_context(
    *,
    agent: str,
    transport: str = "cli",
    cwd: Path | str = ".",
    query: str = "",
    mode: str = "standard",
    target_tokens: int | None = None,
    hard_token_limit: int | None = None,
    debug: bool = False,
    work_signal: dict[str, object] | None = None,
    reason: str = "startup",
    ai_workroot_home: Path | str | None = None,
) -> str:
    explicit_work_signal = WorkSignal.from_dict(work_signal).to_dict() if work_signal else None
    resolved_home = resolve_ai_workroot_home(ai_workroot_home)
    config = load_context_control_config(resolved_home)
    resolved_target_tokens = target_tokens if target_tokens is not None else config.default_target_tokens
    resolved_hard_token_limit = hard_token_limit if hard_token_limit is not None else config.default_hard_token_limit
    budget_source = "cli" if target_tokens is not None or hard_token_limit is not None else "config"
    if (
        resolved_target_tokens <= 0
        or resolved_hard_token_limit <= 0
        or resolved_target_tokens > resolved_hard_token_limit
    ):
        raise ValueError("invalid context token budget")
    startup_response = _startup_response(
        agent=agent,
        transport=transport,
        cwd=cwd,
        query=query,
        work_signal=explicit_work_signal,
        reason=reason,
        ai_workroot_home=resolved_home,
    )
    return _build_context_package(
        _ContextRequest(
            agent=agent,
            cwd=Path(cwd),
            query=query,
            mode=mode,
            target_tokens=resolved_target_tokens,
            hard_token_limit=resolved_hard_token_limit,
            debug=debug,
            budget_source=budget_source,
            startup_response=startup_response,
            startup_guidance=render_private_packet_markdown(
                startup_response, adapter="cli", agent=agent, transport=transport
            ),
            work_signal=explicit_work_signal,
        ),
        ai_workroot_home=resolved_home,
    )


def _startup_response(
    *,
    agent: str,
    transport: str,
    cwd: Path | str,
    query: str,
    work_signal: dict[str, object] | None,
    reason: str,
    ai_workroot_home: Path,
) -> dict[str, object]:
    signal = work_signal or {
        "phase": "orienting",
        "work_kind": "",
        "intended_action": "inspect",
        "focus": query,
        "concerns": [],
    }
    response = startup_context(
        {
            "protocol_version": PROTOCOL_VERSION,
            "request_id": f"req-context-{uuid.uuid4().hex}",
            "agent": {"name": agent, "transport": transport or "cli"},
            "cwd": str(cwd),
            "reason": reason or "startup",
            "query": query,
            "known_state": {},
            "work_signal": signal,
        },
        ai_workroot_home=ai_workroot_home,
    )
    if work_signal is not None:
        response["request_work_signal"] = signal
    return response


__all__ = ["build_context"]
