"""System Health doctor runtime flow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_workroot.agent.native_entry import NativeAgentEntryError, validate_managed_block
from ai_workroot.runtime.registry import find_workroot_by_cwd
from ai_workroot.storage.sqlite import initialize_workroot_sqlite


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
    if sqlite_path.is_file():
        initialize_workroot_sqlite(sqlite_path)
        findings.append(DoctorFinding("PASS", "SQLite schema is initialized"))
    else:
        findings.append(DoctorFinding("FAIL", "missing workroot SQLite database"))

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
