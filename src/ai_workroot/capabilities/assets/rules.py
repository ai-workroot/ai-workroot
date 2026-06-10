"""Asset output directory rules and guide rendering."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from ai_workroot.state.versions import now_utc


DEFAULT_OUTPUT_DIRECTORY = "workroot-output"
GUIDE_FILENAME = "START_HERE.txt"
RULES_RELATIVE_PATH = Path("config/asset-rules.json")
GUIDE_VERSION_MARKER = "WORKROOT_GUIDE_VERSION=1"


@dataclass(frozen=True)
class AssetDirectoryRule:
    rule_id: str
    workroot_id: str
    asset_kind: str
    path: str
    role: str
    source: str
    confidence: str
    writable: bool
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class AssetRuleSet:
    rules: tuple[AssetDirectoryRule, ...]


@dataclass(frozen=True)
class SelectedOutputPath:
    relative_path: str
    absolute_path: Path

    def ensure_parent(self) -> None:
        self.absolute_path.parent.mkdir(parents=True, exist_ok=True)


def ensure_default_asset_rules(*, state_directory: Path, user_directory: Path, workroot_id: str) -> None:
    state_directory = state_directory.expanduser().resolve()
    user_directory = user_directory.expanduser().resolve()
    output_dir = _resolve_user_relative_directory(user_directory, DEFAULT_OUTPUT_DIRECTORY)
    output_dir.mkdir(parents=True, exist_ok=True)

    guide = output_dir / GUIDE_FILENAME
    if not guide.exists() or _is_workroot_owned_guide(guide):
        guide.write_text(render_start_here_guide(), encoding="utf-8")

    timestamp = now_utc()
    existing = load_asset_rules(state_directory)
    previous = _rule_by_id(existing.rules, "rule-default-output")
    default_rule = AssetDirectoryRule(
        rule_id="rule-default-output",
        workroot_id=workroot_id,
        asset_kind="*",
        path=DEFAULT_OUTPUT_DIRECTORY,
        role="default_output",
        source="system_default",
        confidence="high",
        writable=True,
        created_at=previous.created_at if previous else timestamp,
        updated_at=timestamp,
    )
    _write_rule_set(state_directory, AssetRuleSet(tuple(_upsert_rule(existing.rules, default_rule))))


def load_asset_rules(state_directory: Path) -> AssetRuleSet:
    path = state_directory.expanduser().resolve() / RULES_RELATIVE_PATH
    if not path.is_file():
        return AssetRuleSet(())
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return AssetRuleSet(())
    if not isinstance(parsed, dict):
        return AssetRuleSet(())
    values = parsed.get("rules")
    if not isinstance(values, list):
        return AssetRuleSet(())
    return AssetRuleSet(tuple(_rule_from_json(item) for item in values if isinstance(item, dict)))


def save_declared_output_rule(
    *,
    state_directory: Path,
    user_directory: Path,
    workroot_id: str,
    asset_kind: str,
    path: str,
) -> AssetDirectoryRule:
    state_directory = state_directory.expanduser().resolve()
    user_directory = user_directory.expanduser().resolve()
    normalized_kind = _normalize_asset_kind(asset_kind)
    normalized_path = _normalize_rule_path(path)
    _resolve_user_relative_directory(user_directory, normalized_path)

    timestamp = now_utc()
    rule_id = f"rule-output-{_slug(normalized_kind)}"
    existing = load_asset_rules(state_directory)
    previous = _rule_by_id(existing.rules, rule_id)
    rule = AssetDirectoryRule(
        rule_id=rule_id,
        workroot_id=workroot_id,
        asset_kind=normalized_kind,
        path=normalized_path,
        role="declared_output",
        source="user_declared",
        confidence="high",
        writable=True,
        created_at=previous.created_at if previous else timestamp,
        updated_at=timestamp,
    )
    _write_rule_set(state_directory, AssetRuleSet(tuple(_upsert_rule(existing.rules, rule))))
    return rule


def select_output_path(
    *,
    state_directory: Path,
    user_directory: Path,
    asset_kind: str,
    filename: str,
    explicit_path: str = "",
) -> SelectedOutputPath:
    user_directory = user_directory.expanduser().resolve()
    if explicit_path:
        relative_path = _normalize_asset_path(explicit_path)
    else:
        rule = _matching_output_rule(load_asset_rules(state_directory), asset_kind)
        base = rule.path if rule else DEFAULT_OUTPUT_DIRECTORY
        relative_path = f"{_normalize_rule_path(base)}/{_normalize_filename(filename)}"

    absolute_path = (user_directory / relative_path).resolve()
    if absolute_path != user_directory and user_directory not in absolute_path.parents:
        raise ValueError("asset output path escapes user directory")
    return SelectedOutputPath(relative_path=relative_path, absolute_path=absolute_path)


def compact_output_rules(state_directory: Path, *, limit: int = 5) -> list[dict[str, str]]:
    rules: list[dict[str, str]] = []
    for rule in load_asset_rules(state_directory).rules:
        if not rule.writable or rule.role not in {"declared_output", "default_output"}:
            continue
        rules.append({"asset_kind": rule.asset_kind, "path": rule.path, "role": rule.role})
    rules.sort(key=lambda item: (item["role"] != "declared_output", item["asset_kind"], item["path"]))
    return rules[:limit]


def render_start_here_guide() -> str:
    lines = [
        "AI Workroot Start Here",
        "",
        "This folder is the default place for new AI-generated outputs.",
        "",
        "1. Where new outputs go by default",
        "If you do not specify a location, new reports, plans, summaries, and other outputs go here.",
        "",
        "2. Tell the AI your preferred folders",
        "You can say:",
        "Put future reports in reports/.",
        "Put meeting notes in notes/.",
        "Put project plans in plans/.",
        "",
        "3. Build a local knowledge index",
        "You can say:",
        "Build a local knowledge index for docs/.",
        "",
        "4. Continue or preserve work",
        "You can say:",
        "Continue the last task.",
        "Save this decision.",
        "Register this file as an output.",
        "",
        "5. Existing folders",
        "Workroot does not modify existing folders unless you ask. You can keep using ordinary language.",
        "",
        GUIDE_VERSION_MARKER,
        "",
    ]
    return "\n".join(lines)


def _matching_output_rule(rules: AssetRuleSet, asset_kind: str) -> AssetDirectoryRule | None:
    normalized_kind = _normalize_asset_kind(asset_kind)
    for role in ("declared_output", "default_output"):
        candidates = [
            rule
            for rule in rules.rules
            if rule.role == role and rule.writable and rule.asset_kind in {normalized_kind, "*"}
        ]
        if candidates:
            return candidates[-1]
    return None


def _resolve_user_relative_directory(user_directory: Path, relative_path: str) -> Path:
    normalized = _normalize_rule_path(relative_path)
    resolved = (user_directory / normalized).resolve()
    if resolved != user_directory and user_directory not in resolved.parents:
        raise ValueError("asset rule path escapes user directory")
    return resolved


def _normalize_asset_kind(value: str) -> str:
    return str(value or "*").strip().lower() or "*"


def _normalize_rule_path(path: str) -> str:
    raw_input = str(path or "").replace("\\", "/").strip()
    if not raw_input or raw_input.startswith("/") or Path(raw_input).is_absolute():
        raise ValueError("asset rule path must be relative")
    raw = raw_input.strip("/")
    parts = [part for part in raw.split("/") if part not in {"", "."}]
    if not parts or any(part == ".." for part in parts):
        raise ValueError("asset rule path must be relative")
    return "/".join(parts)


def _normalize_asset_path(path: str) -> str:
    raw_input = str(path or "").replace("\\", "/").strip()
    if not raw_input or raw_input.startswith("/") or Path(raw_input).is_absolute():
        raise ValueError("asset path must be relative")
    raw = raw_input.strip("/")
    parts = [part for part in raw.split("/") if part not in {"", "."}]
    if not parts or any(part == ".." for part in parts):
        raise ValueError("asset path must be relative")
    return "/".join(parts)


def _normalize_filename(filename: str) -> str:
    raw = Path(str(filename or "output.md").strip()).name
    return raw or "output.md"


def _is_workroot_owned_guide(path: Path) -> bool:
    try:
        return GUIDE_VERSION_MARKER in path.read_text(encoding="utf-8")
    except OSError:
        return False


def _rule_by_id(rules: tuple[AssetDirectoryRule, ...], rule_id: str) -> AssetDirectoryRule | None:
    for rule in rules:
        if rule.rule_id == rule_id:
            return rule
    return None


def _upsert_rule(existing: tuple[AssetDirectoryRule, ...], rule: AssetDirectoryRule) -> list[AssetDirectoryRule]:
    rules = [item for item in existing if item.rule_id != rule.rule_id]
    rules.append(rule)
    return rules


def _write_rule_set(state_directory: Path, rules: AssetRuleSet) -> None:
    path = state_directory.expanduser().resolve() / RULES_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"rules": [_rule_to_json(rule) for rule in rules.rules]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _rule_from_json(value: dict[str, Any]) -> AssetDirectoryRule:
    return AssetDirectoryRule(
        rule_id=str(value.get("rule_id") or ""),
        workroot_id=str(value.get("workroot_id") or ""),
        asset_kind=str(value.get("asset_kind") or "*"),
        path=str(value.get("path") or ""),
        role=str(value.get("role") or ""),
        source=str(value.get("source") or ""),
        confidence=str(value.get("confidence") or "normal"),
        writable=bool(value.get("writable")),
        created_at=str(value.get("created_at") or ""),
        updated_at=str(value.get("updated_at") or ""),
    )


def _rule_to_json(rule: AssetDirectoryRule) -> dict[str, Any]:
    return {
        "rule_id": rule.rule_id,
        "workroot_id": rule.workroot_id,
        "asset_kind": rule.asset_kind,
        "path": rule.path,
        "role": rule.role,
        "source": rule.source,
        "confidence": rule.confidence,
        "writable": rule.writable,
        "created_at": rule.created_at,
        "updated_at": rule.updated_at,
    }


def _slug(value: str) -> str:
    return "".join(char if char.isalnum() else "-" for char in value.lower()).strip("-") or "asset"
