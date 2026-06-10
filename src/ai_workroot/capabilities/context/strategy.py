"""Plan-driven context recall strategy."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class DisclosureLevel(str, Enum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


@dataclass(frozen=True)
class LeaseFocusSignal:
    status: str = "missing"
    freshness: str = "unknown"
    debug_reason: str = ""

    def trace_payload(self) -> dict[str, str]:
        payload = {
            "status": self.status or "missing",
            "freshness": self.freshness or "unknown",
        }
        if self.debug_reason:
            payload["reason"] = self.debug_reason
        return payload


@dataclass(frozen=True)
class FocusBoundary:
    workroot_id: str
    task_ref: str = ""
    run_ref: str = ""
    confidence: str = "none"
    reason: str = ""


@dataclass(frozen=True)
class StrategyRequest:
    query: str
    mode: str
    focus: FocusBoundary
    target_tokens: int
    hard_token_limit: int
    work_signal: dict[str, Any] | None = None
    lease_signal: LeaseFocusSignal | None = None


@dataclass(frozen=True)
class RecallSource:
    name: str
    level: DisclosureLevel
    scope: str
    limit: int


@dataclass(frozen=True)
class EvidenceDecision:
    requested: bool = False
    detail_mode: str = "map_only"
    refs: tuple[str, ...] = ()
    reason: str = "not_requested"

    def trace_payload(self) -> dict[str, object]:
        return {
            "requested": self.requested,
            "detailMode": self.detail_mode,
            "refs": list(self.refs),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class RecallPlan:
    intent: str
    allowed_levels: tuple[DisclosureLevel, ...]
    sources: tuple[RecallSource, ...]
    debug_reasons: tuple[str, ...]
    lease_signal: LeaseFocusSignal = LeaseFocusSignal()
    semantic_source: str = "conservative"
    evidence_decision: EvidenceDecision = EvidenceDecision()

    def allows(self, level: DisclosureLevel) -> bool:
        return level in self.allowed_levels

    def source_limit(self, name: str, *, default: int = 0) -> int:
        limits = [source.limit for source in self.sources if source.name == name]
        return max(limits) if limits else default

    def source_scope(self, name: str, *, default: str = "") -> str:
        for source in self.sources:
            if source.name == name and source.scope:
                return source.scope
        return default

    def trace_payload(self) -> dict[str, object]:
        return {
            "intent": self.intent,
            "levels": ",".join(level.value for level in self.allowed_levels),
            "sources": [source.name for source in self.sources],
            "reasons": list(self.debug_reasons),
            "leaseSignal": self.lease_signal.trace_payload(),
            "semanticSource": self.semantic_source,
            "evidenceDecision": self.evidence_decision.trace_payload(),
        }


def build_recall_plan(request: StrategyRequest) -> RecallPlan:
    intent, semantic_source = _classify_intent(request)
    lease_signal = request.lease_signal or LeaseFocusSignal()
    evidence_decision = _evidence_decision(intent, request, lease_signal)
    levels = _apply_lease_safety(_allowed_levels(intent, request), lease_signal, request)
    sources = _sources_for_intent(intent, request, levels, semantic_source=semantic_source)
    debug_reasons = [f"intent:{intent}"]
    debug_reasons.append(f"semantic:{semantic_source}")
    if evidence_decision.requested:
        debug_reasons.append(f"evidence:{evidence_decision.detail_mode}")
    if lease_signal.status and lease_signal.status != "missing":
        debug_reasons.append(f"lease:{lease_signal.status}")
    return RecallPlan(
        intent=intent,
        allowed_levels=levels,
        sources=sources,
        debug_reasons=tuple(debug_reasons),
        lease_signal=lease_signal,
        semantic_source=semantic_source,
        evidence_decision=evidence_decision,
    )


def _classify_intent(request: StrategyRequest) -> tuple[str, str]:
    signal_intent = _classify_work_signal_intent(request)
    if signal_intent:
        return signal_intent, "work_signal"
    if request.focus.confidence not in {"high", "medium"}:
        return "unknown", "conservative"
    return "orient", "conservative"


def _classify_work_signal_intent(request: StrategyRequest) -> str:
    signal = request.work_signal if isinstance(request.work_signal, dict) else {}
    if not signal:
        return ""
    work_kind = _text(signal.get("work_kind"))
    intended_action = _canonical_intended_action(signal.get("intended_action"))
    concerns = _concerns(signal)
    if _text(signal.get("intended_action")) in _EVIDENCE_ACTION_ALIASES:
        concerns.add("needs_evidence")
    refs = _refs(signal)
    if "recovering_from_interruption" in concerns:
        return "recover"
    if "needs_evidence" in concerns:
        return "evidence_lookup"
    if intended_action == "edit":
        return "edit_asset"
    if intended_action == "answer" or work_kind == "quick":
        return "answer"
    if intended_action == "review" or work_kind == "review":
        return "review_history"
    if intended_action == "decide" or work_kind == "decision":
        return "decide"
    if intended_action == "inspect" and refs:
        return "inspect"
    if work_kind == "continuation":
        return "continue_work"
    if intended_action == "inspect":
        return "inspect"
    if intended_action == "diagnose" or work_kind == "investigation":
        return "knowledge_lookup"
    return ""


def _allowed_levels(intent: str, request: StrategyRequest) -> tuple[DisclosureLevel, ...]:
    refs = _refs(request.work_signal if request.work_signal else {})
    if intent == "evidence_lookup":
        if refs:
            return (DisclosureLevel.L1, DisclosureLevel.L2, DisclosureLevel.L3)
        return (DisclosureLevel.L1, DisclosureLevel.L2)
    if intent in {"edit_asset", "knowledge_lookup"}:
        return (DisclosureLevel.L1, DisclosureLevel.L2, DisclosureLevel.L3)
    if intent == "inspect":
        if not _has_scope(request, refs):
            return (DisclosureLevel.L1, DisclosureLevel.L2)
        return (DisclosureLevel.L1, DisclosureLevel.L2, DisclosureLevel.L3)
    if intent in {"continue_work", "recover", "review_history", "decide", "handoff"}:
        return (DisclosureLevel.L1, DisclosureLevel.L2)
    if intent == "orient" and request.focus.confidence in {"high", "medium"}:
        return (DisclosureLevel.L1, DisclosureLevel.L2)
    return (DisclosureLevel.L1,)


def _apply_lease_safety(
    levels: tuple[DisclosureLevel, ...],
    lease_signal: LeaseFocusSignal,
    request: StrategyRequest,
) -> tuple[DisclosureLevel, ...]:
    if DisclosureLevel.L3 not in levels:
        return levels
    has_refs = bool(_refs(request.work_signal if request.work_signal else {}))
    if lease_signal.status in {"state_conflict", "interrupted", "multiple_recent"}:
        if lease_signal.status == "interrupted" and has_refs:
            return levels
        return tuple(level for level in levels if level != DisclosureLevel.L3)
    if lease_signal.status == "expired" and lease_signal.freshness != "fresh" and not has_refs:
        return tuple(level for level in levels if level != DisclosureLevel.L3)
    return levels


def _sources_for_intent(
    intent: str,
    request: StrategyRequest,
    levels: tuple[DisclosureLevel, ...],
    *,
    semantic_source: str,
) -> tuple[RecallSource, ...]:
    scope = f"task:{request.focus.task_ref}" if request.focus.task_ref else "workroot:current"
    discovery_scope = _discovery_scope(intent, request, scope, semantic_source=semantic_source)
    refs = _refs(request.work_signal if request.work_signal else {})
    sources: list[RecallSource] = [RecallSource("current_task", DisclosureLevel.L1, scope, 1)]
    sources.extend(
        (
            RecallSource(
                "context_recall_hints",
                DisclosureLevel.L1,
                discovery_scope,
                _mode_limit(request.mode, 4, 8, 16, 24),
            ),
            RecallSource(
                "context_candidates",
                DisclosureLevel.L1,
                discovery_scope,
                _mode_limit(request.mode, 2, 8, 12, 16),
            ),
        )
    )
    if refs:
        sources.append(
            RecallSource("ref_candidates", DisclosureLevel.L1, scope, _mode_limit(request.mode, 4, 8, 12, 16))
        )
    if DisclosureLevel.L2 in levels:
        sources.extend(
            (
                RecallSource("current_handoff", DisclosureLevel.L2, scope, 1),
                RecallSource("task_summary", DisclosureLevel.L2, scope, 2),
                RecallSource("assets", DisclosureLevel.L1, scope, 5),
                RecallSource("decisions", DisclosureLevel.L2, scope, 3),
                RecallSource("relationships", DisclosureLevel.L2, scope, _mode_limit(request.mode, 0, 10, 16, 24)),
            )
        )
    if DisclosureLevel.L3 in levels:
        if intent == "inspect" and not _has_scope(request, _refs(request.work_signal if request.work_signal else {})):
            return tuple(sources)
        if refs:
            sources.append(
                RecallSource("ref_indexed_chunks", DisclosureLevel.L3, scope, _mode_limit(request.mode, 2, 3, 6, 8))
            )
        if intent == "knowledge_lookup":
            sources.append(
                RecallSource("indexed_chunks", DisclosureLevel.L3, scope, _mode_limit(request.mode, 2, 3, 6, 8))
            )
    return tuple(sources)


def _discovery_scope(intent: str, request: StrategyRequest, default_scope: str, *, semantic_source: str) -> str:
    if semantic_source == "conservative" and request.query.strip() and intent in {"orient", "unknown"}:
        return "workroot:current"
    return default_scope


def _evidence_decision(
    intent: str,
    request: StrategyRequest,
    lease_signal: LeaseFocusSignal,
) -> EvidenceDecision:
    signal = request.work_signal if isinstance(request.work_signal, dict) else {}
    refs = _refs(signal)
    requested = intent in {"evidence_lookup", "inspect", "edit_asset"} and bool(refs)
    concerns = _concerns(signal)
    if intent == "evidence_lookup" or "needs_evidence" in concerns:
        requested = True
    if not requested:
        return EvidenceDecision()
    if not refs:
        return EvidenceDecision(
            requested=True,
            detail_mode="summary_with_refs",
            refs=(),
            reason="explicit_ref_required",
        )
    if lease_signal.status in {"state_conflict", "multiple_recent"}:
        return EvidenceDecision(
            requested=True,
            detail_mode="summary_with_refs",
            refs=refs,
            reason=f"lease_{lease_signal.status}",
        )
    return EvidenceDecision(
        requested=True,
        detail_mode="ref_scoped_evidence",
        refs=refs,
        reason="explicit_ref",
    )


def _mode_limit(mode: str, fast: int, standard: int, quality: int, deep: int) -> int:
    normalized = (mode or "standard").strip().lower()
    if normalized == "fast":
        return fast
    if normalized == "quality":
        return quality
    if normalized == "deep":
        return deep
    return standard


_INTENDED_ACTION_ALIASES = {
    "record": "preserve",
    "save": "preserve",
    "lookup": "inspect",
    "find": "inspect",
    "explain": "inspect",
    "rationale": "inspect",
    "evidence": "inspect",
    "source": "inspect",
    "proof": "inspect",
    "justify": "inspect",
}
_EVIDENCE_ACTION_ALIASES = {"explain", "rationale", "evidence", "source", "proof", "justify"}


def _canonical_intended_action(value: object) -> str:
    text = _text(value)
    return _INTENDED_ACTION_ALIASES.get(text, text)


def _has_scope(request: StrategyRequest, refs: tuple[str, ...]) -> bool:
    if refs:
        return True
    return bool(request.focus.task_ref and request.focus.confidence in {"high", "medium"})


def _concerns(signal: dict[str, Any]) -> set[str]:
    values = signal.get("concerns")
    if not isinstance(values, list):
        return set()
    return {str(value).strip() for value in values if str(value).strip()}


def _refs(signal: dict[str, Any]) -> tuple[str, ...]:
    values = signal.get("refs")
    if not isinstance(values, list):
        return ()
    return tuple(str(value).strip() for value in values if str(value).strip())


def _text(value: object) -> str:
    return str(value or "").strip()
