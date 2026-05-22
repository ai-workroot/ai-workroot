"""Safety guards for E2E harness run roots and cleanup."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import shlex
import shutil
import sys
from typing import Sequence
from uuid import uuid4

from tests.e2e.harness import REPO_ROOT


SANDBOX_SENTINEL = ".ai-workroot-e2e-sandbox"
OWNED_SENTINEL = ".ai-workroot-owned"
OWNED_CHILD_DIRS = ("ai-workroot-home", "home", "user-dirs", "reports", "transcripts")
E2E_OPT_IN_ENV = "AI_WORKROOT_RUN_E2E"
E2E_OPT_IN_VALUE = "1"
E2E_OPT_IN_MESSAGE = (
    "E2E tests are opt-in only. Set AI_WORKROOT_RUN_E2E=1 and run "
    "python3 -m tests.e2e.runner --suite <suite>."
)


@dataclass(frozen=True)
class CommandSafetyDecision:
    classification: str
    reason: str


def e2e_opt_in_enabled() -> bool:
    return os.environ.get(E2E_OPT_IN_ENV) == E2E_OPT_IN_VALUE


def require_e2e_opt_in() -> bool:
    if e2e_opt_in_enabled():
        return True
    print(E2E_OPT_IN_MESSAGE, file=sys.stderr)
    return False


def ensure_not_real_repo_cwd_for_live_e2e(cwd: str | Path, *, source_repo: Path = REPO_ROOT) -> None:
    resolved = Path(cwd).expanduser().resolve()
    repo = source_repo.resolve()
    if resolved == repo:
        raise ValueError(f"live-agent E2E must not run from the real repository checkout: {repo}")
    if repo in resolved.parents:
        raise ValueError(f"live-agent E2E must not run inside the real repository checkout: {resolved}")


def default_sandbox_base() -> Path:
    return Path.home() / "tmp" / "ai-workroot-e2e-sandboxes"


def new_default_run_root(*, base: Path | None = None) -> Path:
    sandbox_base = (base or default_sandbox_base()).expanduser().resolve()
    run_id = f"run-{datetime.now(timezone.utc).strftime('%Y-%m-%d-%H-%M-%S')}-{uuid4().hex[:8]}"
    return sandbox_base / run_id


def validate_run_root(
    run_root: str | Path,
    *,
    source_repo: Path = REPO_ROOT,
    sandbox_base: Path | None = None,
) -> Path:
    raw = str(run_root).strip()
    if raw in {"", ".", "..", "/"}:
        raise ValueError(f"unsafe E2E run root: {raw or '<empty>'}")

    resolved = Path(raw).expanduser().resolve()
    repo = source_repo.resolve()
    home = Path.home().resolve()
    forbidden = {
        Path("/").resolve(),
        Path.cwd().resolve(),
        home,
        repo,
        repo.parent,
        repo.parent.parent,
    }
    ai_workroot_home = os.environ.get("AI_WORKROOT_HOME")
    if ai_workroot_home:
        forbidden.add(Path(ai_workroot_home).expanduser().resolve())

    if resolved in forbidden:
        raise ValueError(f"unsafe E2E run root: {resolved}")
    if repo in resolved.parents:
        raise ValueError(f"E2E run root must not be inside the repository: {resolved}")
    resolved_sandbox_base = (sandbox_base or default_sandbox_base()).expanduser().resolve()
    if resolved.parent != resolved_sandbox_base:
        raise ValueError(f"E2E run root must be an immediate run-* child of sandbox base: {resolved_sandbox_base}")
    return resolved


def prepare_run_root(run_root: str | Path, *, sandbox_base: Path | None = None) -> Path:
    resolved = validate_run_root(run_root, sandbox_base=sandbox_base)
    if not resolved.name.startswith("run-"):
        raise ValueError(f"E2E run root must be a unique run-* directory: {resolved}")
    if resolved.exists():
        _assert_sandbox_sentinel(resolved)
        _quarantine_existing_owned_children(resolved, sandbox_base=sandbox_base)
    else:
        resolved.mkdir(parents=True)
    (resolved / SANDBOX_SENTINEL).touch()
    for name in OWNED_CHILD_DIRS:
        child = resolved / name
        child.mkdir(parents=True, exist_ok=True)
        (child / OWNED_SENTINEL).touch()
    return resolved


def safe_quarantine_owned_path(target: str | Path, *, run_root: str | Path, sandbox_base: Path | None = None) -> Path:
    root = validate_run_root(run_root, sandbox_base=sandbox_base)
    _assert_sandbox_sentinel(root)
    resolved = Path(target).expanduser().resolve()
    if resolved == root or root not in resolved.parents:
        raise ValueError(f"cleanup target must be inside E2E run root: {resolved}")
    _assert_owned_sentinel(resolved)

    quarantine_root = _quarantine_root(root)
    destination = _unique_destination(quarantine_root / resolved.name)
    shutil.move(str(resolved), str(destination))
    return destination


def classify_shell_command(command: str | Sequence[str]) -> CommandSafetyDecision:
    if isinstance(command, str):
        if _has_same_line_env_reference(command):
            return CommandSafetyDecision("forbidden", "same-line environment assignment referenced by command")
        try:
            tokens = shlex.split(command)
        except ValueError:
            return CommandSafetyDecision("unknown", "command could not be parsed")
    else:
        tokens = list(command)
    if not tokens:
        return CommandSafetyDecision("unknown", "empty command")

    executable = Path(tokens[0]).name
    if executable == "rm" and any("r" in token or "f" in token for token in tokens[1:] if token.startswith("-")):
        return CommandSafetyDecision("destructive", "recursive or forced rm")
    if executable == "find" and "-delete" in tokens:
        return CommandSafetyDecision("destructive", "find -delete")
    if executable == "git" and len(tokens) >= 2:
        if tokens[1] == "clean":
            return CommandSafetyDecision("destructive", "git clean")
        if tokens[1] == "reset" and "--hard" in tokens:
            return CommandSafetyDecision("destructive", "git reset --hard")
        if tokens[1] in {"push", "tag"}:
            return CommandSafetyDecision("forbidden", f"git {tokens[1]} is forbidden in E2E")
    return CommandSafetyDecision("safe", "no destructive pattern detected")


def _quarantine_existing_owned_children(run_root: Path, *, sandbox_base: Path | None = None) -> None:
    quarantine_root = _quarantine_root(run_root)
    for child in tuple(run_root.iterdir()):
        if child.name == SANDBOX_SENTINEL:
            continue
        if child.name == "reports":
            _quarantine_report_contents(child, quarantine_root)
            continue
        safe_quarantine_owned_path(child, run_root=run_root, sandbox_base=sandbox_base)


def _quarantine_report_contents(reports_dir: Path, quarantine_root: Path) -> None:
    _assert_owned_sentinel(reports_dir)
    report_archive = _unique_destination(quarantine_root / "reports")
    for child in tuple(reports_dir.iterdir()):
        if child.name in {OWNED_SENTINEL, "quarantine"}:
            continue
        report_archive.mkdir(parents=True, exist_ok=True)
        shutil.move(str(child), str(_unique_destination(report_archive / child.name)))


def _quarantine_root(run_root: Path) -> Path:
    reports = run_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / OWNED_SENTINEL).touch()
    quarantine = reports / "quarantine" / _timestamp_id()
    quarantine.mkdir(parents=True, exist_ok=True)
    return quarantine


def _assert_sandbox_sentinel(run_root: Path) -> None:
    if not (run_root / SANDBOX_SENTINEL).is_file():
        raise ValueError(f"missing E2E sandbox sentinel: {run_root / SANDBOX_SENTINEL}")


def _assert_owned_sentinel(path: Path) -> None:
    if not path.is_dir() or not (path / OWNED_SENTINEL).is_file():
        raise ValueError(f"missing E2E owned sentinel: {path / OWNED_SENTINEL}")


def _unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(1, 1000):
        candidate = path.with_name(f"{path.name}-{index}")
        if not candidate.exists():
            return candidate
    raise ValueError(f"could not allocate quarantine destination for {path}")


def _timestamp_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ%f")


def _has_same_line_env_reference(command: str) -> bool:
    assignments = re.findall(r"(?:^|\s)([A-Za-z_][A-Za-z0-9_]*)=[^\s]+", command)
    return any(re.search(rf"\$(?:{{{re.escape(name)}}}|{re.escape(name)})(?:\W|$)", command) for name in assignments)
