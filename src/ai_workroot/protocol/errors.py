"""Workroot Agent Protocol errors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from ai_workroot.protocol.response import (
    empty_workroot_contract,
    guidance_text,
    result_payload,
    semantic_response,
    workroot_view,
)


class ProtocolError(ValueError):
    def __init__(self, code: str, message: Optional[str] = None, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(code if message is None else f"{code}: {message}")
        self.code = code
        self.details = details or {}


@dataclass(frozen=True)
class ErrorResponse:
    code: str
    message: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}


def protocol_error_response(
    code: str,
    *,
    details: Optional[dict[str, Any]] = None,
    next_action: str = "Call sync and retry if still relevant.",
    result_status: str = "resync_required",
) -> dict[str, Any]:
    contract = empty_workroot_contract(next_action="sync", reason="protocol_error")
    return semantic_response(
        ok=False,
        agent_may_continue=True,
        workroot_guidance=guidance_text(
            focus="recovery",
            summary=code,
            next_exchange_action="sync",
            warning=next_action,
        ),
        workroot_contract=contract,
        workroot_view=workroot_view(
            focus="recovery",
            task_brief=code,
            confidence="none",
            why="protocol request error",
            warnings=[next_action],
        ),
        result=result_payload(recorded=False, projected=False, accepted=False, status=result_status),
        error={"code": code, "message": code, "details": details or {}},
    )
