"""Workroot Agent Protocol errors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


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
) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {"code": code, "message": code, "details": details or {}},
        "directive": {
            "type": "resync_required",
            "goal": None,
            "next_action": next_action,
            "expected_events": [],
            "required_before_stop": [],
            "must_not": [],
            "ask_user_when": [],
            "metadata": {},
        },
        "warnings": [],
    }
