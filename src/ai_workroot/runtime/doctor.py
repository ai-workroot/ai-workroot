"""System Health doctor runtime flow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import ast
import subprocess

from ai_workroot.agent.native_entry import NativeAgentEntryError, validate_managed_block
from ai_workroot.runtime.release_validation import validate_release_surface
from ai_workroot.runtime.registry import find_workroot_by_cwd
from ai_workroot.storage.sqlite import verify_workroot_sqlite


@dataclass(frozen=True)
class DoctorFinding:
    status: str
    message: str


@dataclass(frozen=True)
class DoctorResult:
    status: str
    findings: tuple[DoctorFinding, ...]

    def render_text(self) -> str:
        lines = [f"AI Workroot doctor: {self.status}"]
        for finding in self.findings:
            lines.append(f"- {finding.status}: {finding.message}")
        return "\n".join(lines) + "\n"


def run_doctor(*, cwd: Path | str = ".", ai_workroot_home: Path | str | None = None) -> DoctorResult:
    findings: list[DoctorFinding] = []
    try:
        record = find_workroot_by_cwd(cwd, ai_workroot_home=ai_workroot_home)
        findings.append(DoctorFinding("PASS", f"registered Workroot {record['workrootId']}"))
    except ValueError as exc:
        return DoctorResult("FAIL", (DoctorFinding("FAIL", str(exc)),))

    state_directory = Path(record["stateDirectory"])
    user_directory = Path(record["userDirectory"])
    if state_directory.exists() and user_directory not in state_directory.parents:
        findings.append(DoctorFinding("PASS", "managed state is outside user directory"))
    else:
        findings.append(DoctorFinding("FAIL", "managed state boundary is invalid"))

    sqlite_path = state_directory / "cache/workroot.sqlite"
    sqlite_issues = verify_workroot_sqlite(sqlite_path)
    if not sqlite_issues:
        findings.append(DoctorFinding("PASS", "SQLite schema is initialized"))
    else:
        findings.extend(DoctorFinding("FAIL", issue) for issue in sqlite_issues)

    for filename in ("AGENTS.md", "CLAUDE.md"):
        path = user_directory / filename
        if not path.exists():
            continue
        try:
            validate_managed_block(path.read_text(encoding="utf-8"))
        except (NativeAgentEntryError, ValueError) as exc:
            findings.append(DoctorFinding("FAIL", f"{filename} is not a safe Native Agent Entry: {exc}"))
        else:
            findings.append(DoctorFinding("PASS", f"{filename} Native Agent Entry is safe"))

    status = "PASS" if all(finding.status != "FAIL" for finding in findings) else "FAIL"
    return DoctorResult(status, tuple(findings))


def run_release_doctor(root: Path | str = ".") -> DoctorResult:
    repo = Path(root).expanduser().resolve()
    release_surface_errors: list[str] = []
    validate_release_surface(repo, release_surface_errors)
    findings = [
        _check_path(repo, "src/ai_workroot/core", "core package"),
        _check_path(repo, "src/ai_workroot/contracts", "contracts package"),
        _check_path(repo, "src/ai_workroot/runtime", "runtime package"),
        _check_path(repo, "src/ai_workroot/storage", "storage package"),
        _check_path(repo, "src/ai_workroot/indexing/providers", "indexing providers"),
        _check_path(repo, "src/ai_workroot/agent/native_entry.py", "Agent Interface"),
        _check_path(repo, "src/ai_workroot/resources/templates/native_agent_entry/AGENTS.md.template", "Native Agent Entry templates"),
        _check_path(repo, "tests/negative/test_release_control_protection.py", "Release Control protection tests"),
        _check_path(repo, "install/unix/install.sh", "Clean Workroot install script"),
        _check_import_boundaries(repo),
        _check_no_remote_vector_dependency(repo),
        _check_public_seed_quarantine(repo),
        _check_release_surface(release_surface_errors),
    ]
    status = "PASS" if all(finding.status != "FAIL" for finding in findings) else "FAIL"
    return DoctorResult(status, tuple(findings))


def _check_path(repo: Path, rel: str, label: str) -> DoctorFinding:
    return DoctorFinding("PASS" if (repo / rel).exists() else "FAIL", f"{label}: {rel}")


def _check_import_boundaries(repo: Path) -> DoctorFinding:
    errors: list[str] = []
    contracts = repo / "src/ai_workroot/contracts"
    core = repo / "src/ai_workroot/core"
    cli = repo / "src/ai_workroot/cli"
    _scan_forbidden_imports(contracts, ("ai_workroot.",), errors)
    _scan_forbidden_imports(core, ("ai_workroot.storage", "ai_workroot.indexing", "ai_workroot.agent", "ai_workroot.cli"), errors)
    _scan_forbidden_imports(cli, ("ai_workroot.storage", "ai_workroot.indexing"), errors)
    if errors:
        return DoctorFinding("FAIL", "import boundaries: " + "; ".join(errors[:3]))
    return DoctorFinding("PASS", "import boundaries")


def _scan_forbidden_imports(directory: Path, forbidden: tuple[str, ...], errors: list[str]) -> None:
    for path in directory.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            module_names: list[str] = []
            if isinstance(node, ast.Import):
                module_names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                module_names.append(node.module)
            for module in module_names:
                if module.startswith(forbidden):
                    errors.append(f"{path.name} imports {module}")


def _check_no_remote_vector_dependency(repo: Path) -> DoctorFinding:
    forbidden = ("openai", "requests", "httpx", "chromadb", "faiss")
    for path in (repo / "src/ai_workroot").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            module_names: list[str] = []
            if isinstance(node, ast.Import):
                module_names.extend(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                module_names.append(node.module.split(".")[0])
            if any(module in forbidden for module in module_names):
                return DoctorFinding("FAIL", f"remote/vector dependency found in {path.relative_to(repo)}")
    return DoctorFinding("PASS", "no remote LLM, remote embedding, or vector database dependency")


def _check_public_seed_quarantine(repo: Path) -> DoctorFinding:
    seed_paths = ("AGENTS.md", "CLAUDE.md", "space", ".workroot")
    tracked_seed_paths = _tracked_paths(repo, seed_paths)
    if tracked_seed_paths:
        return DoctorFinding("FAIL", "tracked Public Seed root paths: " + ", ".join(tracked_seed_paths))
    ignored_local = [path for path in seed_paths if (repo / path).exists()]
    if ignored_local:
        return DoctorFinding("PASS", "Public Seed quarantine: ignored local root entries only")
    return DoctorFinding("PASS", "Public Seed quarantine: complete")


def _check_release_surface(errors: list[str]) -> DoctorFinding:
    if errors:
        return DoctorFinding("FAIL", "release surface: " + "; ".join(errors[:3]))
    return DoctorFinding("PASS", "release surface")


def _tracked_paths(repo: Path, paths: tuple[str, ...]) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--", *paths],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]
