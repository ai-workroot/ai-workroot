"""Core Context Control model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextBudget:
    target_tokens: int
    hard_token_limit: int

    def __post_init__(self) -> None:
        if self.target_tokens <= 0:
            raise ValueError("target_tokens must be positive")
        if self.hard_token_limit <= 0:
            raise ValueError("hard_token_limit must be positive")
        if self.target_tokens > self.hard_token_limit:
            raise ValueError("target_tokens must not exceed hard_token_limit")

    def requires_trim(self, estimated_tokens: int) -> bool:
        return estimated_tokens > self.hard_token_limit

    def final_fallback(self, rendered_package: str) -> str:
        return rendered_package[: self.hard_token_limit]
