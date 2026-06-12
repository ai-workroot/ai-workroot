"""Live Codex + Workroot task-continuity long-run harness."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
from typing import Any

from ai_workroot.state.layout import workroot_sqlite_path
from ai_workroot.state.registry import list_workroots
from tests.e2e.harness import REPO_ROOT, env_for, run_cli, validate_user_directory, write_user_files
from tests.e2e.live_agent import REMOTE_LLM_OPT_IN_ENV, build_live_agent_environment
from tests.e2e.live_protocol import REMOTE_AUTH_ENV, REMOTE_ENV, classify_workroot_commands
from tests.e2e.personas import Persona
from tests.e2e.safety import OWNED_SENTINEL, ensure_not_real_repo_cwd_for_live_e2e, prepare_run_root


ROUNDS_ENV = "AI_WORKROOT_E2E_LIVE_TASK_ROUNDS"
ROLE_ENV = "AI_WORKROOT_E2E_LIVE_TASK_ROLE"
DEFAULT_ROUND_COUNT = 10
MAX_ROUND_COUNT = 20
MAX_SINGLE_ROLE_ROUND_COUNT = 50
SUITE_NAME = "live-task-continuity"
SYNC_PACKET_MAX_BYTES = 3600


@dataclass(frozen=True)
class LiveRoundScript:
    index: int
    label: str
    user_request: str
    expected_shapes: tuple[str, ...] = ()
    expected_asset_paths: tuple[str, ...] = ()
    expected_asset_owners: tuple[tuple[str, str], ...] = ()
    expected_context_intent: str = ""


@dataclass(frozen=True)
class LiveRoleScenario:
    slug: str
    name: str
    workroot_id: str
    mode: str
    user_files: dict[str, str]
    rounds: tuple[LiveRoundScript, ...]
    expected_final_owner: str = ""

    @property
    def persona(self) -> Persona:
        return Persona(
            slug=self.slug,
            name=self.name,
            workroot_id=self.workroot_id,
            native_agent_entry=True,
            user_files=self.user_files,
        )


@dataclass(frozen=True)
class LiveTaskRoundResult:
    role_slug: str
    round_index: int
    transcript_dir: Path
    stdout_path: Path
    stderr_path: Path
    last_message_path: Path
    command_log_path: Path
    db_summary_path: Path
    returncode: int
    failures: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.returncode == 0 and not self.failures and self.last_message_path.is_file()


@dataclass(frozen=True)
class LiveTaskRoleResult:
    role_slug: str
    user_directory: Path
    round_results: tuple[LiveTaskRoundResult, ...]
    final_db_summary: dict[str, Any]
    failures: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return all(round_result.passed for round_result in self.round_results) and not self.failures


@dataclass(frozen=True)
class LiveTaskContinuityResult:
    run_root: Path
    ai_workroot_home: Path
    summary_path: Path
    audit_path: Path
    role_results: tuple[LiveTaskRoleResult, ...]

    @property
    def returncode(self) -> int:
        return 0 if all(result.passed for result in self.role_results) else 1

    def failure_report(self) -> str:
        lines = [f"summary={self.summary_path}", f"audit={self.audit_path}"]
        for role in self.role_results:
            for failure in role.failures:
                lines.append(f"{role.role_slug}: {failure}")
            for round_result in role.round_results:
                for failure in round_result.failures:
                    lines.append(f"{role.role_slug}/round-{round_result.round_index:02d}: {failure}")
                if round_result.returncode != 0:
                    lines.append(f"{role.role_slug}/round-{round_result.round_index:02d}: rc={round_result.returncode}")
                    lines.append(f"stderr={round_result.stderr_path}")
        return "\n".join(lines)


def resolve_round_count(value: str | None, *, single_role: bool = False) -> int:
    if value is None or not str(value).strip():
        return DEFAULT_ROUND_COUNT
    max_rounds = MAX_SINGLE_ROLE_ROUND_COUNT if single_role else MAX_ROUND_COUNT
    try:
        count = int(str(value).strip())
    except ValueError as exc:
        raise ValueError(f"{ROUNDS_ENV} must be an integer") from exc
    if count < 1 or count > max_rounds:
        raise ValueError(f"{ROUNDS_ENV} must be between 1 and {max_rounds}")
    return count


def live_task_continuity_scenarios(
    *,
    round_count: int | None = None,
    role_slug: str | None = None,
) -> tuple[LiveRoleScenario, ...]:
    count = round_count or DEFAULT_ROUND_COUNT
    max_rounds = MAX_SINGLE_ROLE_ROUND_COUNT if role_slug else MAX_ROUND_COUNT
    if count < 1 or count > max_rounds:
        raise ValueError(f"round_count must be between 1 and {max_rounds}")
    if role_slug == "live-mixed-complexity":
        return (
            LiveRoleScenario(
                slug="live-mixed-complexity",
                name="Live Mixed Complexity Operator",
                workroot_id="wr_live_mixed_complexity",
                mode="long_cycle",
                user_files={
                    "founder-notes.md": "# Founder Notes\n\nPricing cadence, onboarding risk, and interview plan.\n",
                    "engineering-notes.md": "# Engineering Notes\n\nProtocol continuity and runtime view checks.\n",
                    "metrics.csv": "metric,value\nactivation,0.42\nhandoff_quality,0.55\nasset_recall,0.38\n",
                    "roadmap.md": "# Roadmap\n\nImprove protocol UX without adding visible user noise.\n",
                },
                rounds=_select_rounds(_mixed_complexity_rounds(), count),
            ),
        )
    if role_slug == "live-chinese-founder-operator":
        return (
            LiveRoleScenario(
                slug="live-chinese-founder-operator",
                name="Live Chinese Founder Operator",
                workroot_id="wr_live_chinese_founder_operator",
                mode="long_cycle",
                user_files={
                    "客户访谈记录.md": (
                        "# 客户访谈记录\n\n"
                        "- 华东制造企业关注部署周期和权限边界。\n"
                        "- 连锁零售客户关注门店知识库同步和一线使用成本。\n"
                        "- 金融科技客户关注审计、留痕和私有化交付。\n"
                    ),
                    "试点指标.csv": (
                        "指标,当前值,目标值\n首周激活率,0.28,0.55\n有效问题解决率,0.41,0.70\n人工接力次数,18,8\n"
                    ),
                    "产品约束.md": (
                        "# 产品约束\n\n"
                        "试点版本必须保持交付简单，不把内部协议暴露给普通业务用户。\n"
                        "销售承诺要围绕真实业务流程，不承诺尚未验证的自动化能力。\n"
                    ),
                },
                rounds=_select_rounds(_chinese_founder_operator_rounds(), count),
            ),
        )
    if role_slug == "live-novice-chinese-shop-owner":
        return (
            LiveRoleScenario(
                slug="live-novice-chinese-shop-owner",
                name="Live Novice Chinese Shop Owner",
                workroot_id="wr_live_novice_chinese_shop_owner",
                mode="long_cycle",
                user_files={
                    "店铺现状.md": (
                        "# 店铺现状\n\n"
                        "社区咖啡店，工作日早高峰人多，下午空档明显。"
                        "主要客群是附近上班族、宝妈和周末亲子家庭。\n"
                    ),
                    "本月流水.csv": ("项目,金额\n咖啡,18500\n轻食,7600\n活动收入,1200\n会员充值,5200\n"),
                    "顾客反馈.md": (
                        "# 顾客反馈\n\n"
                        "- 很多人希望有早餐套餐。\n"
                        "- 下午想要安静办公位。\n"
                        "- 周末亲子活动有人问，但店员觉得组织起来麻烦。\n"
                    ),
                },
                rounds=_select_rounds(_novice_chinese_shop_owner_rounds(), count),
                expected_final_owner="咖啡",
            ),
        )
    if role_slug == "live-novice-english-community-builder":
        return (
            LiveRoleScenario(
                slug="live-novice-english-community-builder",
                name="Live Novice English Community Builder",
                workroot_id="wr_live_novice_english_community_builder",
                mode="long_cycle",
                user_files={
                    "community-notes.md": (
                        "# Community Notes\n\n"
                        "Small local community for independent designers. People ask for critique, referrals, "
                        "and lightweight accountability.\n"
                    ),
                    "member-feedback.csv": (
                        "segment,signal\nnew_member,wants easier first event\nactive_member,wants critique night\n"
                        "sponsor,wants clearer audience description\n"
                    ),
                    "constraints.md": (
                        "# Constraints\n\n"
                        "The organizer has three hours per week. Events should be simple, low cost, and easy to repeat.\n"
                    ),
                },
                rounds=_select_rounds(_novice_english_community_builder_rounds(), count),
            ),
        )
    if role_slug == "live-novice-chinese-service-owner":
        return (
            LiveRoleScenario(
                slug="live-novice-chinese-service-owner",
                name="Live Novice Chinese Service Owner",
                workroot_id="wr_live_novice_chinese_service_owner",
                mode="long_cycle",
                user_files={
                    "门店现状.md": (
                        "# 门店现状\n\n"
                        "县城家政培训门店，主要做月嫂、育儿嫂、保洁和养老陪护介绍。"
                        "老板自己懂业务但不懂软件，希望把招生、培训、客户交付和阿姨管理理顺。\n"
                    ),
                    "学员与阿姨情况.csv": (
                        "类型,人数,主要问题\n新学员,36,怕学完接不到单\n可上岗阿姨,28,服务标准不统一\n"
                        "老客户转介绍,17,回访不稳定\n投诉记录,5,沟通预期不清楚\n"
                    ),
                    "客户反馈.md": (
                        "# 客户反馈\n\n"
                        "- 客户最担心阿姨临时请假和服务边界说不清。\n"
                        "- 新手妈妈希望先听一节体验课再交钱。\n"
                        "- 老年陪护客户更看重稳定和应急联系人。\n"
                    ),
                    "现金流记录.csv": (
                        "项目,金额\n本月报名收入,42600\n阿姨介绍服务费,23800\n房租水电,9200\n广告投放,6800\n老师课酬,14800\n"
                    ),
                    "下月想法.md": (
                        "# 下月想法\n\n"
                        "想做一次社区活动，一次短视频直播，另外考虑招聘一个兼职招生顾问。"
                        "老板担心一下子做太多，店员跟不上。\n"
                    ),
                },
                rounds=_select_rounds(_novice_chinese_service_owner_rounds(), count),
                expected_final_owner="家政",
            ),
        )
    bases = (
        _founder_operator_rounds(),
        _software_engineer_rounds(),
        _analyst_researcher_rounds(),
        _inbox_adhoc_rounds(),
        _product_manager_rounds(),
    )
    roles = (
        LiveRoleScenario(
            slug="live-founder-operator",
            name="Live Founder Operator",
            workroot_id="wr_live_founder_operator",
            mode="long_cycle",
            user_files={
                "pricing-notes.md": "# Pricing Notes\n\nEnterprise onboarding risk and expansion signals.\n",
                "customer-feedback.csv": "account,signal\nalpha,needs onboarding\nbeta,asks for annual plan\n",
            },
            rounds=_select_rounds(bases[0], count),
        ),
        LiveRoleScenario(
            slug="live-software-engineer",
            name="Live Software Engineer",
            workroot_id="wr_live_software_engineer",
            mode="long_cycle",
            user_files={
                "README.md": "# Refactor Sandbox\n\nSmall service refactor notes.\n",
                "src/service.py": "def calculate(value):\n    return value + 1\n",
            },
            rounds=_select_rounds(bases[1], count),
        ),
        LiveRoleScenario(
            slug="live-analyst-researcher",
            name="Live Analyst Researcher",
            workroot_id="wr_live_analyst_researcher",
            mode="investigation",
            user_files={
                "data.csv": "segment,signal\nnew,high churn\nretained,expansion\n",
                "notes.md": "# Research Notes\n\nLook for durable conclusions and evidence.\n",
            },
            rounds=_select_rounds(bases[2], count),
        ),
        LiveRoleScenario(
            slug="live-inbox-adhoc",
            name="Live Inbox Adhoc",
            workroot_id="wr_live_inbox_adhoc",
            mode="temporary",
            user_files={
                "scratch.md": "# Scratch\n\nTemporary discussion area.\n",
                "questions.md": "# Questions\n\nLoose questions arrive here.\n",
            },
            rounds=_select_rounds(bases[3], count),
        ),
        LiveRoleScenario(
            slug="live-product-manager",
            name="Live Product Manager",
            workroot_id="wr_live_product_manager",
            mode="long_cycle",
            user_files={
                "roadmap.md": "# Roadmap\n\nProtocol UX and recall quality.\n",
                "feedback.md": "# Feedback\n\nUsers want continuity without protocol noise.\n",
            },
            rounds=_select_rounds(bases[4], count),
        ),
    )
    if role_slug:
        filtered = tuple(role for role in roles if role.slug == role_slug)
        if not filtered:
            raise ValueError(f"unknown live task continuity role: {role_slug}")
        return filtered
    return roles


def create_audited_workroot_wrapper(*, run_root: Path) -> Path:
    bin_dir = run_root / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    (bin_dir / OWNED_SENTINEL).touch()
    wrapper = bin_dir / "workroot"
    wrapper.write_text(
        """#!/usr/bin/env python3
from __future__ import annotations
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
log_path = os.environ.get("WORKROOT_COMMAND_LOG")
artifacts_dir = os.environ.get("WORKROOT_COMMAND_ARTIFACTS_DIR")
command = [sys.executable, "-m", "ai_workroot", *sys.argv[1:]]
completed = subprocess.run(command, text=True, capture_output=True, check=False)
ended = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
stdout_path = ""
stderr_path = ""
if artifacts_dir:
    root = Path(artifacts_dir)
    root.mkdir(parents=True, exist_ok=True)
    command_id = f"cmd-{started.replace(':', '').replace('-', '')}-{uuid4().hex[:8]}"
    stdout = root / f"{command_id}-stdout.txt"
    stderr = root / f"{command_id}-stderr.txt"
    stdout.write_text(completed.stdout, encoding="utf-8")
    stderr.write_text(completed.stderr, encoding="utf-8")
    stdout_path = str(stdout)
    stderr_path = str(stderr)
if log_path:
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "argv": sys.argv[1:],
            "cwd": os.getcwd(),
            "returncode": completed.returncode,
            "startedAt": started,
            "endedAt": ended,
            "stdoutPath": stdout_path,
            "stderrPath": stderr_path,
            "stdoutBytes": len(completed.stdout.encode("utf-8")),
            "stderrBytes": len(completed.stderr.encode("utf-8")),
        }, ensure_ascii=False, sort_keys=True) + "\\n")
sys.stdout.write(completed.stdout)
sys.stderr.write(completed.stderr)
raise SystemExit(completed.returncode)
""",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    return wrapper


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def runtime_artifacts_in_user_directory(
    user_directory: Path,
    *,
    allowed_asset_paths: tuple[str, ...] = (),
) -> list[str]:
    allowed = {_normalize_relative_path(path) for path in allowed_asset_paths}
    disallowed_names = {
        "cache",
        "runtime",
        "transcripts",
        "workroot-command-log.jsonl",
        "db-summary.json",
        "codex-stdout.txt",
        "codex-stderr.txt",
        "codex-last-message.txt",
        "intent.json",
        "progress.json",
        "handoff.json",
        "request.json",
        "result.json",
    }
    artifacts: list[str] = []
    for entry in user_directory.rglob("*"):
        rel = _normalize_relative_path(str(entry.relative_to(user_directory)))
        if rel in allowed:
            continue
        if entry.name in disallowed_names or entry.name.startswith("cmd-"):
            artifacts.append(rel)
    return sorted(artifacts)


def summarize_role_database(*, ai_home: Path, workroot_id: str) -> dict[str, Any]:
    record = _workroot_record(ai_home=ai_home, workroot_id=workroot_id)
    state_directory = Path(record["stateDirectory"])
    sqlite_path = workroot_sqlite_path(state_directory)
    with sqlite3.connect(sqlite_path) as conn:
        counts = {
            "tasks": _count(conn, "tasks"),
            "taskRuns": _count(conn, "task_runs"),
            "taskItems": _count(conn, "task_items"),
            "taskSummaries": _count(conn, "task_summaries"),
            "taskSummariesCurrent": _count_where(conn, "task_summaries", "status = 'current'"),
            "handoffs": _count(conn, "handoffs"),
            "handoffsCurrent": _count_where(conn, "handoffs", "status = 'current' AND task_id IS NOT NULL"),
            "assets": _count(conn, "assets"),
            "relationshipEdges": _count(conn, "relationship_edges"),
            "contextCandidates": _count(conn, "context_candidates"),
            "indexedFiles": _count(conn, "indexed_files"),
            "indexedChunks": _count(conn, "indexed_chunks"),
            "protocolEvents": _count(conn, "protocol_events"),
            "protocolCommitBatches": _count(conn, "protocol_commit_batches"),
        }
        return {
            "sqlitePath": str(sqlite_path),
            "stateDirectory": str(state_directory),
            "runtimeViewDirectories": _runtime_view_directories(state_directory),
            "runtimeFileCount": _runtime_file_count(state_directory),
            "counts": counts,
            "tasks": _tasks(conn),
            "taskRuns": _task_runs(conn),
            "taskProliferation": _task_proliferation(conn),
            "protocolEventStatuses": _group_count(conn, "protocol_events", "status"),
            "protocolEventKinds": _group_count(conn, "protocol_events", "kind"),
            "commitBatchStatuses": _group_count(conn, "protocol_commit_batches", "status"),
            "assetPaths": _asset_paths(conn),
            "assetOwners": _asset_owners(conn),
            "contextCandidateSources": _group_count(conn, "context_candidates", "source_type"),
            "latestHandoff": _latest_handoff(conn),
        }


def run_live_task_continuity(
    *,
    run_root: Path,
    sandbox_base: Path | None = None,
    round_count: int | None = None,
    role_slug: str | None = None,
) -> LiveTaskContinuityResult:
    if os.environ.get(REMOTE_LLM_OPT_IN_ENV) != "1":
        raise RuntimeError(f"{SUITE_NAME} E2E requires {REMOTE_LLM_OPT_IN_ENV}=1")
    resolved_role_slug = role_slug or os.environ.get(ROLE_ENV) or None
    resolved_rounds = (
        resolve_round_count(str(round_count), single_role=bool(resolved_role_slug))
        if round_count is not None
        else resolve_round_count(os.environ.get(ROUNDS_ENV), single_role=bool(resolved_role_slug))
    )
    run_root = prepare_run_root(run_root, sandbox_base=sandbox_base)
    ai_workroot_home = run_root / "ai-workroot-home"
    env = env_for(ai_workroot_home)
    codex = shutil.which("codex")
    if not codex:
        raise RuntimeError("codex CLI is not available")
    wrapper = create_audited_workroot_wrapper(run_root=run_root)

    role_results = tuple(
        _run_role(
            role=role,
            run_root=run_root,
            ai_workroot_home=ai_workroot_home,
            env=env,
            codex=codex,
            wrapper=wrapper,
        )
        for role in live_task_continuity_scenarios(round_count=resolved_rounds, role_slug=resolved_role_slug)
    )
    summary_path = _write_summary(run_root=run_root, ai_workroot_home=ai_workroot_home, role_results=role_results)
    audit_path = _write_audit(run_root=run_root, role_results=role_results, summary_path=summary_path)
    return LiveTaskContinuityResult(
        run_root=run_root,
        ai_workroot_home=ai_workroot_home,
        summary_path=summary_path,
        audit_path=audit_path,
        role_results=role_results,
    )


def _run_role(
    *,
    role: LiveRoleScenario,
    run_root: Path,
    ai_workroot_home: Path,
    env: dict[str, str],
    codex: str,
    wrapper: Path,
) -> LiveTaskRoleResult:
    user_directory = run_root / "user-dirs" / role.slug
    write_user_files(user_directory, role.user_files)
    init = run_cli(
        (
            "init",
            "--name",
            role.name,
            "--directory",
            str(user_directory),
            "--id",
            role.workroot_id,
            "--native-agent-entry",
        ),
        env=env,
        cwd=REPO_ROOT,
    )
    if init.returncode != 0:
        raise RuntimeError(init.stderr or init.stdout)
    failures = validate_user_directory(role.persona, user_directory, ai_workroot_home)
    ensure_not_real_repo_cwd_for_live_e2e(user_directory)

    round_results: list[LiveTaskRoundResult] = []
    for round_script in role.rounds:
        before_db = summarize_role_database(ai_home=ai_workroot_home, workroot_id=role.workroot_id)
        result = _run_round(
            role=role,
            round_script=round_script,
            run_root=run_root,
            ai_workroot_home=ai_workroot_home,
            user_directory=user_directory,
            env=env,
            codex=codex,
            wrapper=wrapper,
            before_db_summary=before_db,
        )
        round_results.append(result)

    final_db = summarize_role_database(ai_home=ai_workroot_home, workroot_id=role.workroot_id)
    role_command_records = [read_jsonl(round_result.command_log_path) for round_result in round_results]
    failures.extend(_validate_role_protocol_usage(role_command_records))
    failures.extend(_validate_role_continuity(role=role, user_directory=user_directory, final_db=final_db))
    return LiveTaskRoleResult(
        role_slug=role.slug,
        user_directory=user_directory,
        round_results=tuple(round_results),
        final_db_summary=final_db,
        failures=tuple(failures),
    )


def _run_round(
    *,
    role: LiveRoleScenario,
    round_script: LiveRoundScript,
    run_root: Path,
    ai_workroot_home: Path,
    user_directory: Path,
    env: dict[str, str],
    codex: str,
    wrapper: Path,
    before_db_summary: dict[str, Any],
) -> LiveTaskRoundResult:
    transcript_dir = run_root / "transcripts" / SUITE_NAME / role.slug / f"round-{round_script.index:02d}"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = transcript_dir / "prompt.txt"
    stdout_path = transcript_dir / "codex-stdout.txt"
    stderr_path = transcript_dir / "codex-stderr.txt"
    last_message_path = transcript_dir / "codex-last-message.txt"
    command_log_path = transcript_dir / "workroot-command-log.jsonl"
    db_summary_path = transcript_dir / "db-summary.json"
    artifacts_dir = transcript_dir / "command-artifacts"
    prompt = _round_prompt(role=role, round_script=round_script)
    prompt_path.write_text(prompt + "\n", encoding="utf-8")

    live_env = build_live_agent_environment(env, run_root=run_root)
    live_env.update(
        {
            "PATH": f"{wrapper.parent}:{os.environ.get('PATH', '')}",
            "WORKROOT_COMMAND_LOG": str(command_log_path),
            "WORKROOT_COMMAND_ARTIFACTS_DIR": str(artifacts_dir),
        }
    )
    command = _codex_command(
        codex=codex,
        user_directory=user_directory,
        ai_workroot_home=ai_workroot_home,
        last_message_path=last_message_path,
        prompt=prompt,
        extra_writable_dirs=(transcript_dir, wrapper.parent),
    )
    completed = subprocess.run(
        command,
        cwd=user_directory,
        env=live_env,
        text=True,
        capture_output=True,
        check=False,
        timeout=420,
    )
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    db_summary = summarize_role_database(ai_home=ai_workroot_home, workroot_id=role.workroot_id)
    command_records = read_jsonl(command_log_path)
    commands = classify_workroot_commands(command_records)
    round_failures = _validate_round(
        round_script=round_script,
        user_directory=user_directory,
        returncode=completed.returncode,
        last_message_path=last_message_path,
        commands=commands,
        db_summary=db_summary,
        before_db_summary=before_db_summary,
        command_records=command_records,
    )
    db_summary["beforeRound"] = before_db_summary
    db_summary["round"] = round_script.index
    db_summary["commands"] = commands
    db_summary["commandRecords"] = command_records
    db_summary["userDirectoryRuntimeArtifacts"] = runtime_artifacts_in_user_directory(
        user_directory,
        allowed_asset_paths=_all_expected_asset_paths(role),
    )
    db_summary_path.write_text(json.dumps(db_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return LiveTaskRoundResult(
        role_slug=role.slug,
        round_index=round_script.index,
        transcript_dir=transcript_dir,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        last_message_path=last_message_path,
        command_log_path=command_log_path,
        db_summary_path=db_summary_path,
        returncode=completed.returncode,
        failures=tuple(round_failures),
    )


def _round_prompt(*, role: LiveRoleScenario, round_script: LiveRoundScript) -> str:
    if role.slug.startswith("live-novice-"):
        return _novice_round_prompt(role=role, round_script=round_script)
    expected_assets = ", ".join(round_script.expected_asset_paths) or "none"
    expected_shapes = ", ".join(round_script.expected_shapes) or "as-needed"
    context_intent_guidance = _context_intent_guidance(round_script)
    return f"""Live task-continuity E2E.

You are the Codex Agent working inside a sandbox Workroot for role: {role.name}.
Use Workroot privately. Do not show Workroot packets, refs, leases, JSON, or internal paths to the user.
Do not create runtime files in the user directory. If you need files for Workroot command requests, prefer shape-native CLI commands instead.

Round {round_script.index}: {round_script.label}
User request:
{round_script.user_request}

Expected Workroot capture shape(s): {expected_shapes}
Expected user-visible asset path(s): {expected_assets}

Protocol behavior:
1. Start by using `workroot agent sync --format packet` from cwd ".". Do not call top-level `workroot sync`. For recall inside a normal user turn, use sync with `intended_action=inspect`. Use `workroot context` only for startup, recovery, or debugging outside the normal turn loop. Every context or sync call must include `--query` with the current user request or a short intent.
2. Sync with a structured Work Signal:
   - Direct answer: work_kind=quick, intended_action=answer. Do not use boundary=separate_work for quick answers.
   - Continuation, checkpoint, handoff, or continuing an existing inbox: work_kind=continuation. Use intended_action=preserve for checkpoint or handoff; use intended_action=summarize only when summarizing.
   - Decision inside active work: work_kind=decision, intended_action=decide.
   - User-visible file for active work: work_kind=authoring, intended_action=preserve.
   - Separate long-running work: phase=starting, work_kind=task, intended_action=plan, boundary=separate_work.
   - New loose temporary side thought: phase=switching, work_kind=inbox, intended_action=plan.
3. Follow the private packet. When it asks for commit, use `workroot agent commit --format packet --shape ... --lease ...` with concise stable facts.
4. Use `--persistence temporary` only on `workroot agent commit` for inbox or adhoc temporary work. Use `--persistence normal` only on `workroot agent commit` for long-cycle work.
5. If you create a user-visible file, create it first, then commit `--shape asset` with its relative path.
6. If you make a stable decision, commit `--shape decision`.
7. Before stopping or switching, commit `--shape continuation` when Workroot asks for continuity.
8. If Workroot is unavailable or rejects a write, continue helping the user and mention only the user-facing result.
{context_intent_guidance}

Finish with exactly two short user-facing lines. The first line must be:
LIVE_TASK_CONTINUITY_OK {role.slug} round-{round_script.index:02d}
The second line should summarize the useful user-facing result without protocol details.
"""


def _novice_round_prompt(*, role: LiveRoleScenario, round_script: LiveRoundScript) -> str:
    return f"""Live novice task-continuity E2E.

You are the Codex Agent working inside a sandbox Workroot for role: {role.name}.
The user is a normal person using an AI assistant. They do not know Workroot internals.
Use Workroot privately. Do not show Workroot packets, refs, leases, JSON, or internal paths to the user.
Do not create runtime files in the user directory. If you create a useful user-visible result file, keep it in the user's normal output area and then preserve it privately.

Round {round_script.index}: {round_script.label}
User request:
{round_script.user_request}

Private operating rules:
1. Start by using `workroot agent sync --format packet` from cwd "." with `--query` set to the current user request or a short intent.
2. If the user's ordinary language clearly implies durable work, temporary side work, continuation, a decision, evidence lookup, or a user-visible file, include a compact `--work-signal` with stable enum fields and keep `focus` in the user's language.
3. Use `phase=starting, work_kind=task, intended_action=plan, boundary=separate_work` only when the user is starting a separate new long-running goal.
4. Use `work_kind=continuation` when continuing the same direction, `phase=switching, work_kind=inbox` for loose temporary side thoughts, `work_kind=decision` for stable choices, and `intended_action=inspect` with `concerns=["needs_evidence"]` for source, proof, or rationale requests.
5. Follow the private packet. When it asks for commit, use `workroot agent commit --format packet --shape ... --lease ...` with concise stable facts.
6. If Workroot is unavailable or rejects a write, continue helping the user and mention only the user-facing result.

Finish with exactly two short user-facing lines. The first line must be:
LIVE_TASK_CONTINUITY_OK {role.slug} round-{round_script.index:02d}
The second line should summarize the useful user-facing result without protocol details.
"""


def _context_intent_guidance(round_script: LiveRoundScript) -> str:
    if round_script.expected_context_intent != "evidence_lookup":
        return ""
    return (
        "9. This round needs evidence lookup: the first `workroot agent sync` call must include "
        '`--work-signal` with `intended_action=inspect` and `concerns=["needs_evidence"]`, '
        "or an equivalent evidence action alias."
    )


def _codex_command(
    *,
    codex: str,
    user_directory: Path,
    ai_workroot_home: Path,
    last_message_path: Path,
    prompt: str,
    extra_writable_dirs: tuple[Path, ...],
) -> tuple[str, ...]:
    prefix: list[str] = [codex]
    remote = os.environ.get(REMOTE_ENV, "")
    if remote:
        prefix.extend(["--remote", remote])
    remote_auth_token_env = os.environ.get(REMOTE_AUTH_ENV, "")
    if remote_auth_token_env:
        prefix.extend(["--remote-auth-token-env", remote_auth_token_env])
    command = [
        *prefix,
        "exec",
        "--cd",
        str(user_directory),
        "--add-dir",
        str(ai_workroot_home),
    ]
    for directory in extra_writable_dirs:
        command.extend(["--add-dir", str(directory)])
    command.extend(
        [
            "--skip-git-repo-check",
            "--ephemeral",
            "--sandbox",
            "workspace-write",
            "--output-last-message",
            str(last_message_path),
            prompt,
        ]
    )
    return tuple(command)


def _validate_round(
    *,
    round_script: LiveRoundScript,
    user_directory: Path,
    returncode: int,
    last_message_path: Path,
    commands: list[str],
    db_summary: dict[str, Any],
    before_db_summary: dict[str, Any] | None = None,
    command_records: list[dict[str, Any]] | None = None,
) -> list[str]:
    failures: list[str] = []
    if returncode != 0:
        failures.append("codex invocation failed")
    if not last_message_path.is_file():
        failures.append("missing last model message")
    else:
        expected = "LIVE_TASK_CONTINUITY_OK "
        if expected not in last_message_path.read_text(encoding="utf-8"):
            failures.append("last model message missing live continuity marker")
    if not commands:
        failures.append("no Workroot command was called")
    if "agent sync" not in commands:
        failures.append("round did not call agent sync")
    failures.extend(_validate_context_and_sync_queries(command_records or []))
    failures.extend(_validate_agent_sync_format(command_records or []))
    failures.extend(_validate_context_usage(command_records or []))
    failures.extend(_validate_context_intent(round_script, command_records or []))
    failures.extend(_validate_unexpected_start_work(round_script, command_records or []))
    failures.extend(_validate_sync_packet_budget(command_records or []))
    if round_script.expected_shapes and "agent commit" not in commands:
        failures.append(f"expected commit for shapes {round_script.expected_shapes}")
    indexed_assets = {_normalize_relative_path(path) for path in db_summary.get("assetPaths", [])}
    for asset_path in round_script.expected_asset_paths:
        if not (user_directory / asset_path).is_file():
            failures.append(f"expected user asset missing: {asset_path}")
        if _normalize_relative_path(asset_path) not in indexed_assets:
            failures.append(f"expected Workroot asset missing: {asset_path}")
    failures.extend(_validate_asset_owner_expectations(round_script.expected_asset_owners, db_summary))
    if _status_delta(db_summary, before_db_summary, "invalid") > 0:
        failures.append("new invalid protocol events found")
    if _status_delta(db_summary, before_db_summary, "quarantined") > 0:
        failures.append("new quarantined protocol events found")
    for shape in _unrecovered_rejected_commit_shapes(command_records or []):
        failures.append(f"Workroot commit was rejected: {shape}")
    return failures


def _validate_context_and_sync_queries(command_records: list[dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    placeholder_queries = {"<short intent>", "<current user request or short intent>"}
    for record in command_records:
        argv = record.get("argv")
        if not isinstance(argv, list) or not argv:
            continue
        if "--help" in argv:
            continue
        is_context = argv[0] == "context"
        is_agent_sync = len(argv) >= 2 and argv[:2] == ["agent", "sync"]
        if not is_context and not is_agent_sync:
            continue
        query = _arg_value(argv, "--query")
        if not query.strip() or query.strip() in placeholder_queries:
            failures.append(f"{'context' if is_context else 'agent sync'} missing meaningful --query")
    return failures


def _validate_context_usage(command_records: list[dict[str, Any]]) -> list[str]:
    context_count = sum(1 for record in command_records if _record_is_context(record))
    sync_count = sum(1 for record in command_records if _record_is_agent_sync(record))
    if context_count and not sync_count:
        return ["context was used without agent sync"]
    return []


def _validate_agent_sync_format(command_records: list[dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    for record in command_records:
        if not _record_is_agent_sync(record):
            continue
        argv = record.get("argv")
        if not isinstance(argv, list):
            continue
        if _arg_value(argv, "--format") != "packet":
            failures.append("agent sync did not request packet format")
    return failures


def _validate_role_protocol_usage(command_records_by_round: list[list[dict[str, Any]]]) -> list[str]:
    if len(command_records_by_round) <= 1:
        return []
    context_rounds = sum(
        1 for records in command_records_by_round if any(_record_is_context(record) for record in records)
    )
    if context_rounds == len(command_records_by_round):
        return ["context was used in every round; sync-first loop regressed"]
    return []


def _validate_context_intent(round_script: LiveRoundScript, command_records: list[dict[str, Any]]) -> list[str]:
    if round_script.expected_context_intent != "evidence_lookup":
        return []
    protocol_records = [
        record for record in command_records if _record_is_agent_sync(record) or _record_is_context(record)
    ]
    if not protocol_records:
        return ["evidence round missing agent sync"]
    work_signal = _json_arg(protocol_records[0]["argv"], "--work-signal")
    if _has_evidence_signal(work_signal):
        return []
    return ["evidence round sync missing needs_evidence WorkSignal"]


def _validate_unexpected_start_work(
    round_script: LiveRoundScript,
    command_records: list[dict[str, Any]],
) -> list[str]:
    if "start_work" in {_normalize_shape_name(shape) for shape in round_script.expected_shapes}:
        return []
    for record in command_records:
        argv = record.get("argv")
        if not isinstance(argv, list) or len(argv) < 2 or argv[:2] != ["agent", "commit"]:
            continue
        if _normalize_shape_name(_arg_value(argv, "--shape")) == "start_work":
            return ["unexpected start-work commit in round without expected start_work"]
    return []


def _validate_sync_packet_budget(command_records: list[dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    for record in command_records:
        if not _record_is_agent_sync(record):
            continue
        stdout_bytes = int(record.get("stdoutBytes") or 0)
        if stdout_bytes > SYNC_PACKET_MAX_BYTES:
            failures.append(f"sync packet exceeded compact byte budget: {stdout_bytes} > {SYNC_PACKET_MAX_BYTES}")
    return failures


def _record_is_context(record: dict[str, Any]) -> bool:
    argv = record.get("argv")
    return isinstance(argv, list) and bool(argv) and argv[0] == "context"


def _record_is_agent_sync(record: dict[str, Any]) -> bool:
    argv = record.get("argv")
    return isinstance(argv, list) and len(argv) >= 2 and argv[:2] == ["agent", "sync"]


def _normalize_shape_name(value: object) -> str:
    return str(value or "").strip().replace("-", "_")


def _json_arg(argv: list[object], flag: str) -> dict[str, Any]:
    value = _arg_value(argv, flag)
    if not value:
        return {}
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _has_evidence_signal(work_signal: dict[str, Any]) -> bool:
    intended_action = str(work_signal.get("intended_action") or "").strip().lower()
    concerns = work_signal.get("concerns")
    concern_values = {str(item).strip().lower() for item in concerns} if isinstance(concerns, list) else set()
    if "needs_evidence" in concern_values:
        return True
    return intended_action in {"explain", "rationale", "evidence", "source", "proof", "justify"}


def _unrecovered_rejected_commit_shapes(command_records: list[dict[str, Any]]) -> list[str]:
    pending: list[str] = []
    for record in command_records:
        argv = record.get("argv")
        if not isinstance(argv, list) or len(argv) < 2 or argv[:2] != ["agent", "commit"] or "--shape" not in argv:
            continue
        shape = _arg_value(argv, "--shape") or "unknown"
        stdout_path = Path(str(record.get("stdoutPath") or ""))
        if not stdout_path.is_file():
            continue
        stdout = stdout_path.read_text(encoding="utf-8")
        if re.search(r'"accepted"\s*:\s*false', stdout) and re.search(r'"status"\s*:\s*"rejected"', stdout):
            pending.append(shape)
        elif re.search(r'"accepted"\s*:\s*true', stdout) and shape in pending:
            pending.remove(shape)
    return pending


def _arg_value(argv: list[object], flag: str) -> str:
    try:
        index = argv.index(flag)
    except ValueError:
        return ""
    if index + 1 >= len(argv):
        return ""
    return str(argv[index + 1])


def _validate_role_continuity(
    *,
    role: LiveRoleScenario,
    user_directory: Path,
    final_db: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    counts = final_db["counts"]
    if counts["tasks"] < 1:
        failures.append("no task was created")
    if counts["taskRuns"] < 1:
        failures.append("no task run was created")
    if counts["protocolEvents"] < 1:
        failures.append("no protocol event was recorded")
    if _role_requires_continuity_view(role) and counts["handoffsCurrent"] < 1 and counts["taskSummariesCurrent"] < 1:
        failures.append("no current handoff or task summary was preserved")
    proliferation = final_db.get("taskProliferation") if isinstance(final_db.get("taskProliferation"), dict) else {}
    active_roots = int(proliferation.get("activeNormalRootTasks") or 0)
    if role.mode == "long_cycle" and active_roots > 3:
        failures.append(f"task proliferation: active normal root tasks {active_roots} exceeds 3")
    pollution = runtime_artifacts_in_user_directory(user_directory, allowed_asset_paths=_all_expected_asset_paths(role))
    if pollution:
        failures.append(f"user directory runtime pollution: {pollution}")
    expected_assets = _all_expected_asset_paths(role)
    indexed_assets = {_normalize_relative_path(path) for path in final_db.get("assetPaths", [])}
    for asset_path in expected_assets:
        if not (user_directory / asset_path).is_file():
            failures.append(f"expected user asset missing: {asset_path}")
        if _normalize_relative_path(asset_path) not in indexed_assets:
            failures.append(f"expected Workroot asset missing: {asset_path}")
    owner_expectations = tuple(
        expectation for round_script in role.rounds for expectation in round_script.expected_asset_owners
    )
    failures.extend(_validate_asset_owner_expectations(owner_expectations, final_db))
    if role.expected_final_owner:
        latest_handoff = final_db.get("latestHandoff") if isinstance(final_db.get("latestHandoff"), dict) else {}
        task_title = str(latest_handoff.get("taskTitle") or "")
        expected = role.expected_final_owner.strip().lower()
        if expected and expected not in task_title.lower():
            failures.append(f"latest handoff owner drifted away from expected owner: {role.expected_final_owner}")
    return failures


def _validate_asset_owner_expectations(
    expected_asset_owners: tuple[tuple[str, str], ...],
    db_summary: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    asset_owners = db_summary.get("assetOwners") if isinstance(db_summary.get("assetOwners"), dict) else {}
    normalized_owners = {
        _normalize_relative_path(path): [str(owner) for owner in owners]
        for path, owners in asset_owners.items()
        if isinstance(owners, list)
    }
    for raw_path, expected_owner in expected_asset_owners:
        path = _normalize_relative_path(raw_path)
        owners = normalized_owners.get(path, [])
        expected = expected_owner.strip().lower()
        if expected == "workroot":
            if owners:
                failures.append(f"expected asset {path} to be workroot-owned, got task owners: {owners}")
            continue
        if not owners:
            failures.append(f"expected asset {path} owner containing {expected_owner!r}, got no task owner")
            continue
        if not any(expected in owner.lower() for owner in owners):
            failures.append(f"expected asset {path} owner containing {expected_owner!r}, got {owners}")
    return failures


def _write_summary(
    *,
    run_root: Path,
    ai_workroot_home: Path,
    role_results: tuple[LiveTaskRoleResult, ...],
) -> Path:
    path = run_root / "reports" / "live-task-continuity-summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "returncode": 0 if all(role.passed for role in role_results) else 1,
        "aiWorkrootHome": str(ai_workroot_home),
        "roleResults": [
            {
                "roleSlug": role.role_slug,
                "roundCount": len(role.round_results),
                "returncode": 0 if role.passed else 1,
                "failures": list(role.failures),
                "userDirectory": str(role.user_directory),
                "finalDbSummary": role.final_db_summary,
                "roundResults": [
                    {
                        "round": round_result.round_index,
                        "returncode": round_result.returncode,
                        "failures": list(round_result.failures),
                        "transcriptDir": str(round_result.transcript_dir),
                        "lastMessage": str(round_result.last_message_path),
                        "commandLog": str(round_result.command_log_path),
                        "dbSummary": str(round_result.db_summary_path),
                    }
                    for round_result in role.round_results
                ],
            }
            for role in role_results
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _write_audit(
    *,
    run_root: Path,
    role_results: tuple[LiveTaskRoleResult, ...],
    summary_path: Path,
) -> Path:
    path = run_root / "reports" / "live-task-continuity-audit.md"
    lines = [
        "# Live Task Continuity Audit",
        "",
        f"Summary JSON: `{summary_path}`",
        "",
    ]
    for role in role_results:
        counts = role.final_db_summary["counts"]
        status = "PASS" if role.passed else "FAIL"
        lines.extend(
            [
                f"## {role.role_slug}: {status}",
                "",
                f"- rounds: {len(role.round_results)}",
                f"- tasks: {counts['tasks']}",
                f"- task runs: {counts['taskRuns']}",
                f"- task items: {counts['taskItems']}",
                f"- current summaries: {counts['taskSummariesCurrent']}",
                f"- current handoffs: {counts['handoffsCurrent']}",
                f"- assets: {counts['assets']}",
                f"- relationships: {counts['relationshipEdges']}",
                f"- context candidates: {counts['contextCandidates']}",
                f"- protocol events: {counts['protocolEvents']}",
                "",
            ]
        )
        if role.failures:
            lines.append("Failures:")
            lines.extend(f"- {failure}" for failure in role.failures)
            lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _select_rounds(base: tuple[LiveRoundScript, ...], count: int) -> tuple[LiveRoundScript, ...]:
    selected: list[LiveRoundScript] = []
    while len(selected) < count:
        selected.extend(base)
    return tuple(
        LiveRoundScript(
            index=index,
            label=round_script.label,
            user_request=round_script.user_request,
            expected_shapes=round_script.expected_shapes,
            expected_asset_paths=round_script.expected_asset_paths,
            expected_asset_owners=round_script.expected_asset_owners,
            expected_context_intent=round_script.expected_context_intent,
        )
        for index, round_script in enumerate(selected[:count], start=1)
    )


def _founder_operator_rounds() -> tuple[LiveRoundScript, ...]:
    return (
        LiveRoundScript(
            1,
            "Start operating cadence",
            "Start a durable founder operating task for a six-week pricing and onboarding cadence. Preserve the task goal.",
            ("start_work",),
        ),
        LiveRoundScript(
            2,
            "Checkpoint milestones",
            "Continue the operating cadence. Produce three milestone bullets and preserve this checkpoint.",
            ("checkpoint",),
        ),
        LiveRoundScript(
            3,
            "Pricing decision",
            "Choose one pricing experiment for enterprise onboarding and preserve the stable decision.",
            ("decision",),
        ),
        LiveRoundScript(
            4,
            "Plan asset",
            "Create `results/founder-operating-plan.md` with a concise operating plan, then preserve it as a user-visible asset.",
            ("asset",),
            ("results/founder-operating-plan.md",),
        ),
        LiveRoundScript(
            5,
            "Handoff",
            "Preserve a continuation note for the founder operating cadence so the next session can resume.",
            ("continuation",),
        ),
        LiveRoundScript(
            6,
            "Resume",
            "Continue the previous founder operating cadence from Workroot context and add one progress checkpoint.",
            ("checkpoint",),
        ),
        LiveRoundScript(
            7,
            "Risk checkpoint",
            "Review the biggest operational risk and preserve one blocked or open item.",
            ("checkpoint",),
        ),
        LiveRoundScript(
            8, "Decision follow-up", "Make a stable decision about the next customer interview segment.", ("decision",)
        ),
        LiveRoundScript(
            9,
            "Update asset",
            "Update `results/founder-operating-plan.md` with the latest decision and preserve the asset again.",
            ("asset",),
            ("results/founder-operating-plan.md",),
        ),
        LiveRoundScript(
            10,
            "Final handoff",
            "Leave a clear handoff for continuing this founder operating cadence later.",
            ("continuation",),
        ),
    )


def _software_engineer_rounds() -> tuple[LiveRoundScript, ...]:
    return (
        LiveRoundScript(
            1,
            "Start refactor task",
            "Start a durable implementation task to make `src/service.py` easier to reason about. Preserve the task goal.",
            ("start_work",),
        ),
        LiveRoundScript(
            2,
            "Inspect and checkpoint",
            "Inspect the tiny service and preserve a checkpoint with the current implementation understanding.",
            ("checkpoint",),
        ),
        LiveRoundScript(
            3,
            "Implementation decision",
            "Decide whether to keep the function simple or add a helper. Preserve the decision.",
            ("decision",),
        ),
        LiveRoundScript(
            4,
            "Create engineering note",
            "Create `docs/refactor-note.md` with a concise engineering note and preserve it as an asset.",
            ("asset",),
            ("docs/refactor-note.md",),
        ),
        LiveRoundScript(
            5, "Continuation", "Preserve what remains for the refactor task before stopping.", ("continuation",)
        ),
        LiveRoundScript(
            6,
            "Resume implementation",
            "Continue the refactor task and preserve one checkpoint about next code change.",
            ("checkpoint",),
        ),
        LiveRoundScript(
            7,
            "Testing checkpoint",
            "Describe the minimal test to protect this behavior and preserve it as progress.",
            ("checkpoint",),
        ),
        LiveRoundScript(
            8, "Scope decision", "Make a stable scope decision about avoiding unrelated refactors.", ("decision",)
        ),
        LiveRoundScript(
            9,
            "Update engineering note",
            "Update `docs/refactor-note.md` with the testing checkpoint and preserve the asset.",
            ("asset",),
            ("docs/refactor-note.md",),
        ),
        LiveRoundScript(10, "Handoff", "Leave a resume-ready handoff for the implementation task.", ("continuation",)),
    )


def _analyst_researcher_rounds() -> tuple[LiveRoundScript, ...]:
    return (
        LiveRoundScript(
            1,
            "Start investigation",
            "Start a durable investigation task about churn and expansion signals in `data.csv`.",
            ("start_work",),
        ),
        LiveRoundScript(
            2,
            "Checkpoint findings",
            "Summarize the two strongest signals and preserve the checkpoint.",
            ("checkpoint",),
        ),
        LiveRoundScript(
            3,
            "Evidence decision",
            "Decide which signal should be investigated first and preserve the rationale.",
            ("decision",),
        ),
        LiveRoundScript(
            4,
            "Research report asset",
            "Create `reports/signal-investigation.md` with a compact report and preserve it as an asset.",
            ("asset",),
            ("reports/signal-investigation.md",),
        ),
        LiveRoundScript(5, "Handoff", "Preserve the next analysis step as a handoff.", ("continuation",)),
        LiveRoundScript(
            6,
            "Resume investigation",
            "Continue the investigation from Workroot and add one checkpoint.",
            ("checkpoint",),
        ),
        LiveRoundScript(
            7, "Open question", "Preserve one open question that should drive the next data pull.", ("checkpoint",)
        ),
        LiveRoundScript(8, "Decision", "Make a stable decision about the next metric to validate.", ("decision",)),
        LiveRoundScript(
            9,
            "Update report",
            "Update `reports/signal-investigation.md` with the latest metric decision and preserve the asset.",
            ("asset",),
            ("reports/signal-investigation.md",),
        ),
        LiveRoundScript(10, "Final handoff", "Leave a clear handoff for the next analyst session.", ("continuation",)),
    )


def _inbox_adhoc_rounds() -> tuple[LiveRoundScript, ...]:
    return (
        LiveRoundScript(
            1,
            "Temporary inbox start",
            "This is a temporary scattered discussion about possible learning topics. Preserve it only as temporary inbox work.",
            ("start_work",),
        ),
        LiveRoundScript(
            2, "Adhoc checkpoint", "Add a lightweight checkpoint about the most useful topic so far.", ("checkpoint",)
        ),
        LiveRoundScript(
            3,
            "Quick answer",
            "Answer this quick question directly: what is one benefit of keeping task summaries concise?",
            (),
        ),
        LiveRoundScript(
            4, "Temporary decision", "Make a small temporary decision about which topic to revisit next.", ("decision",)
        ),
        LiveRoundScript(
            5,
            "Inbox handoff",
            "Leave a temporary continuation note so this loose conversation can be resumed.",
            ("continuation",),
        ),
        LiveRoundScript(
            6,
            "Resume inbox",
            "Continue the previous temporary inbox discussion and preserve one lightweight checkpoint.",
            ("checkpoint",),
        ),
        LiveRoundScript(
            7, "Adhoc open item", "Add one open item that should not become a formal project yet.", ("checkpoint",)
        ),
        LiveRoundScript(
            8,
            "Tiny asset",
            "Create `notes/inbox-summary.md` with a short summary and preserve it as a user-visible asset.",
            ("asset",),
            ("notes/inbox-summary.md",),
        ),
        LiveRoundScript(
            9, "Temporary handoff", "Preserve a handoff for the temporary inbox discussion.", ("continuation",)
        ),
        LiveRoundScript(
            10,
            "Noisy quick turn",
            "Answer briefly and do not create a new formal project unless Workroot says it is needed.",
            (),
        ),
    )


def _product_manager_rounds() -> tuple[LiveRoundScript, ...]:
    return (
        LiveRoundScript(
            1,
            "Start product planning",
            "Start a durable product planning task about protocol UX and context recall quality.",
            ("start_work",),
        ),
        LiveRoundScript(
            2, "Checkpoint workflow", "Preserve a checkpoint with the core user workflow and risk.", ("checkpoint",)
        ),
        LiveRoundScript(
            3,
            "Product decision",
            "Make a stable product decision about keeping the protocol private and compact.",
            ("decision",),
        ),
        LiveRoundScript(
            4,
            "Planning asset",
            "Create `product/protocol-ux-plan.md` with a compact plan and preserve it as an asset.",
            ("asset",),
            ("product/protocol-ux-plan.md",),
        ),
        LiveRoundScript(5, "Handoff", "Preserve a continuation note for the product planning task.", ("continuation",)),
        LiveRoundScript(
            6,
            "Resume plan",
            "Continue the product planning task and add one checkpoint about rollout.",
            ("checkpoint",),
        ),
        LiveRoundScript(7, "Review risk", "Preserve one risk about model-visible protocol noise.", ("checkpoint",)),
        LiveRoundScript(
            8,
            "Decision update",
            "Make a stable decision about how much packet detail to show the model.",
            ("decision",),
        ),
        LiveRoundScript(
            9,
            "Update plan",
            "Update `product/protocol-ux-plan.md` with the decision and preserve the asset.",
            ("asset",),
            ("product/protocol-ux-plan.md",),
        ),
        LiveRoundScript(
            10, "Final handoff", "Leave a clear product handoff for the next planning session.", ("continuation",)
        ),
    )


def _chinese_founder_operator_rounds() -> tuple[LiveRoundScript, ...]:
    return (
        LiveRoundScript(
            1,
            "Start Chinese founder pilot thread",
            "我想启动一个长期任务：作为创始人推进企业 AI 工作台的首批试点，重点围绕客户分层、定价、交付风险和上下文连续性。请先把任务目标管起来。",
            ("start_work",),
        ),
        LiveRoundScript(
            2,
            "Pilot priorities checkpoint",
            "继续刚才的试点任务。请基于已有客户访谈记录，沉淀三个优先级和一个当前最大的开放风险。",
            ("checkpoint",),
        ),
        LiveRoundScript(
            3,
            "First pilot segment decision",
            "现在需要做一个稳定决策：首批试点客户应该优先选择制造、零售还是金融科技？请给出选择和理由，并把这个决策保存下来。",
            ("decision",),
        ),
        LiveRoundScript(
            4,
            "Create pilot operating plan asset",
            "请创建 `workroot-output/enterprise-ai-pilot-plan.md`，写一份紧凑的试点推进计划，并把这个用户可见结果作为资产登记。",
            ("asset",),
            ("workroot-output/enterprise-ai-pilot-plan.md",),
        ),
        LiveRoundScript(
            5,
            "Pricing checkpoint",
            "继续主线任务，不要重新开始新任务。请把试点定价需要验证的两个问题和一个暂不承诺的边界记录为进展。",
            ("checkpoint",),
        ),
        LiveRoundScript(
            6,
            "Temporary sales-language tangent",
            "临时插一个发散讨论：我想快速想三句销售开场白，这个不要变成正式项目。请按临时 inbox 处理，保存时使用 `--persistence temporary`。",
            ("start_work",),
        ),
        LiveRoundScript(
            7,
            "Temporary sales-language checkpoint",
            "继续刚才临时销售话术讨论，只保留一个最值得下次再看的话术方向，不要把它升级成长期任务。",
            ("checkpoint",),
        ),
        LiveRoundScript(
            8,
            "Resume main pilot after tangent",
            "回到企业 AI 工作台试点主线。请从上下文接上，不要新建主线任务，记录下一步客户访谈排序。",
            ("checkpoint",),
        ),
        LiveRoundScript(
            9,
            "Update pilot operating plan asset",
            "请更新 `workroot-output/enterprise-ai-pilot-plan.md`，补充客户访谈排序和定价边界，并再次登记这个资产。",
            ("asset",),
            ("workroot-output/enterprise-ai-pilot-plan.md",),
        ),
        LiveRoundScript(
            10,
            "Main pilot handoff",
            "请给企业 AI 工作台试点主线留一个接力说明：当前状态、下一步动作、一个需要我决策的问题。",
            ("continuation",),
        ),
        LiveRoundScript(
            11,
            "Start delivery risk thread",
            "现在启动一个相关但独立的长期任务：梳理试点交付风险，重点看部署、权限、审计和一线培训。请把它和主线保持关联但不要混成同一个任务。",
            ("start_work",),
        ),
        LiveRoundScript(
            12,
            "Delivery risk checkpoint",
            "继续交付风险任务。请结合产品约束，记录最重要的交付风险、触发条件和一个缓解动作。",
            ("checkpoint",),
        ),
        LiveRoundScript(
            13,
            "Delivery scope decision",
            "请做一个稳定决策：首批试点是否承诺私有化部署？请保存决策和原因。",
            ("decision",),
        ),
        LiveRoundScript(
            14,
            "Create delivery risk asset",
            "请创建 `workroot-output/delivery-risk-note.md`，写一份交付风险说明，并把这个文件作为资产登记。",
            ("asset",),
            ("workroot-output/delivery-risk-note.md",),
        ),
        LiveRoundScript(
            15,
            "Quick answer without new task",
            "快速回答一个问题即可：为什么不要把所有历史细节都塞进上下文？不要为这个问题新建正式任务。",
            (),
        ),
        LiveRoundScript(
            16,
            "Resume main pilot with metrics",
            "回到企业 AI 工作台试点主线。请根据试点指标表，记录一个最需要追踪的北极星指标和判断理由。",
            ("checkpoint",),
        ),
        LiveRoundScript(
            17,
            "Temporary sales-language handoff",
            "回到临时销售话术讨论，留一个临时接力说明，说明后续如果继续聊应该从哪句话术方向开始。",
            ("continuation",),
        ),
        LiveRoundScript(
            18,
            "Pilot KPI decision",
            "再次回到企业 AI 工作台试点主线。请做一个稳定决策：首批试点最核心的成功指标是什么？保存这个决策。",
            ("decision",),
        ),
        LiveRoundScript(
            19,
            "Create interview script asset",
            "请创建 `workroot-output/customer-interview-script.md`，写一份用于首批试点客户访谈的提纲，并把它作为资产登记。",
            ("asset",),
            ("workroot-output/customer-interview-script.md",),
        ),
        LiveRoundScript(
            20,
            "Final Chinese pilot handoff",
            "请为这轮中文试点任务留下最终接力：主线当前结论、交付风险任务当前结论、临时话术讨论状态，以及下一轮最应该先做什么。",
            ("continuation",),
        ),
    )


def _novice_chinese_shop_owner_rounds() -> tuple[LiveRoundScript, ...]:
    return (
        LiveRoundScript(
            1,
            "Shop planning start",
            "我最近想把社区咖啡店经营得更稳一点，你先帮我整理一个未来一个月的经营方向。",
            ("start_work",),
        ),
        LiveRoundScript(
            2,
            "Morning offer",
            "你看一下店铺现状和流水，帮我想两个早高峰可以试的小动作，别太复杂。",
            ("checkpoint",),
        ),
        LiveRoundScript(
            3,
            "Choose first experiment",
            "这两个里面先做哪个更合适？你直接帮我定一个，并说明为什么。",
            ("decision",),
        ),
        LiveRoundScript(
            4,
            "Create simple plan",
            "帮我写一份给店员看的执行清单，放到 `outputs/shop-month-plan.md`。",
            ("asset",),
            ("outputs/shop-month-plan.md",),
        ),
        LiveRoundScript(
            5,
            "Side idea",
            "我临时想到一个事：周末亲子活动能不能做？先随便帮我想两个点子，不一定真的做。",
            ("start_work",),
        ),
        LiveRoundScript(
            6,
            "Return to main",
            "先回到这个月经营方向，帮我把第一周最该盯的一个数字和原因记下来。",
            ("checkpoint",),
        ),
        LiveRoundScript(
            7,
            "Afternoon issue",
            "下午空档还是头疼，你结合顾客反馈，帮我补一个低成本办法。",
            ("checkpoint",),
        ),
        LiveRoundScript(
            8,
            "Update plan",
            "把刚才定下来的早高峰和下午空档安排补进 `outputs/shop-month-plan.md`。",
            ("asset",),
            ("outputs/shop-month-plan.md",),
        ),
        LiveRoundScript(
            9,
            "Small answer",
            "简单回答一下：为什么我不能同时改早餐、下午办公、周末活动三个方向？",
            (),
        ),
        LiveRoundScript(
            10,
            "Midway pause",
            "我上午先到这里。你帮我记一下现在已经定了什么，下次回来我别忘了先看哪里。",
            ("continuation",),
        ),
        LiveRoundScript(
            11,
            "Create customer message",
            "帮我写一版发朋友圈的小短文，介绍这周早高峰的小活动，放到 `outputs/朋友圈文案.md`。",
            ("asset",),
            ("outputs/朋友圈文案.md",),
        ),
        LiveRoundScript(
            12,
            "Temporary decoration thought",
            "忽然想到店里要不要换几张桌子，这个先不急，你帮我列两个判断标准就行。",
            ("start_work",),
        ),
        LiveRoundScript(
            13,
            "Back to operations",
            "先别管桌子了，回到店里的经营安排。你帮我看一下下午空档那个办法，第一天怎么做最省事？",
            ("checkpoint",),
        ),
        LiveRoundScript(
            14,
            "Evidence request",
            "你刚才说下午可以做安静办公位，这个判断主要是从哪些现有信息看出来的？",
            (),
            expected_context_intent="evidence_lookup",
        ),
        LiveRoundScript(
            15,
            "Update staff plan again",
            "把会员要不要推、下午第一天怎么做，也补进 `outputs/shop-month-plan.md`。",
            ("asset",),
            ("outputs/shop-month-plan.md",),
        ),
        LiveRoundScript(
            16,
            "Quick pricing question",
            "顺手问一句：现在咖啡要不要直接涨一块钱？你先给我一个很短的判断。",
            ("decision",),
        ),
        LiveRoundScript(
            17,
            "Create weekly review sheet",
            "帮我做一张下周每天关店后能填的复盘表，放到 `outputs/下周复盘表.md`。",
            ("asset",),
            ("outputs/下周复盘表.md",),
        ),
        LiveRoundScript(
            18,
            "Resume side idea lightly",
            "周末亲子活动那个事我还没想好，你帮我留一个最小版本，不要影响这个月主安排。",
            ("checkpoint",),
        ),
        LiveRoundScript(
            19,
            "Final prioritization",
            "如果我下周只能盯三件事，你帮我排个顺序，别讲太复杂。",
            ("decision",),
        ),
        LiveRoundScript(
            20,
            "Natural stop",
            "今天先这样。下次我回来，你提醒我先看哪几个结果。",
            ("continuation",),
        ),
    )


def _novice_chinese_service_owner_rounds() -> tuple[LiveRoundScript, ...]:
    return (
        LiveRoundScript(
            1,
            "Service business planning start",
            "我这家家政培训门店最近事情有点乱，招生、培训、阿姨上岗、客户回访都在我脑子里打架。我不懂你们这些工具该怎么用，你就当我在跟一个靠谱助理说话，先帮我把未来一个月最应该抓的经营方向理出来，别写得太虚，也别一上来就让我做很多表格。",
            ("start_work",),
        ),
        LiveRoundScript(
            2,
            "Training and delivery checkpoint",
            "你看一下现有材料，我感觉现在问题不是没人问，而是报名以后能不能学会、学完能不能接到合适的单、客户会不会满意。请帮我把最关键的三个问题按先后顺序排一下，再说明每个问题如果不管会带来什么后果，最好能让我拿去跟店员开十分钟小会。",
            ("checkpoint",),
        ),
        LiveRoundScript(
            3,
            "Choose first operating focus",
            "这三个问题里我不可能同时抓，我店里就三个人，还要正常接客户电话。你帮我直接定一下这个月先抓哪个方向，理由要能说服店员，别给我一堆平均用力的建议，我需要一个明确选择。如果你觉得有些事要先放下，也请直接说出来。",
            ("decision",),
        ),
        LiveRoundScript(
            4,
            "Create one month operating plan",
            "帮我把刚才定下来的方向写成一份店里能执行的一个月安排，不要像咨询报告，最好就是老板和店员每天能照着看的。请放成 `outputs/家政门店一个月经营安排.md` 这个文件，里面要有每周重点、谁来做、怎么判断有没有进展。",
            ("asset",),
            ("outputs/家政门店一个月经营安排.md",),
        ),
        LiveRoundScript(
            5,
            "Temporary live streaming idea",
            "我又想到一个不一定靠谱的点子：有人说让我每晚直播讲月嫂课，但我自己没做过，也怕店员忙不过来。这个先当临时想法，不要影响刚才那个主安排，你帮我快速列一下它可能有用和可能添乱的地方，尤其要提醒我哪些坑别马上踩。",
            ("start_work",),
        ),
        LiveRoundScript(
            6,
            "Return to main training path",
            "先别被直播带跑了，回到家政培训这条主线。我想知道第一周具体应该盯哪个动作，是先改体验课、先整理阿姨服务标准，还是先补客户回访？你结合现有情况给一个落地顺序，并说明第一天就能开始做的最小动作是什么，不要超过店员现在的承受能力。",
            ("checkpoint",),
        ),
        LiveRoundScript(
            7,
            "Create training checklist",
            "请帮我写一份给老师和店员用的培训检查清单，重点是新学员学完之后能不能达到上岗要求，语言要普通人看得懂。文件放到 `outputs/学员上岗检查清单.md`，不要太长，但关键项不能漏，最好让老师明天上课前就能照着改。",
            ("asset",),
            ("outputs/学员上岗检查清单.md",),
        ),
        LiveRoundScript(
            8,
            "Evidence for training priority",
            "你刚才一直强调先把培训和上岗标准理顺，我想确认一下这个判断不是拍脑袋。你主要是从我给你的哪些信息看出来的？请用普通话讲清楚，不要说得像技术说明，也不要把所有原话都堆给我，我只想知道关键依据，以及这个依据是不是足够支持现在先这么做。",
            (),
            expected_context_intent="evidence_lookup",
        ),
        LiveRoundScript(
            9,
            "Pricing package decision",
            "现在有个收费问题我拿不准：体验课要不要免费，还是收一个很低的定金，后面报名再抵扣？你帮我做个明确选择，考虑到县城客户比较敏感，但完全免费又可能来一堆不认真学的人。这个选择最好能兼顾口碑和筛选诚意，也方便前台解释。",
            ("decision",),
        ),
        LiveRoundScript(
            10,
            "Pause with next pickup",
            "我上午先忙客户去了。你帮我把现在已经定下来的东西、还没定的东西、下次回来最先该看的地方整理一下。不要写太多，我希望晚上打开以后能马上接着做，不用重新想一遍，也别让我从头解释门店情况。",
            ("continuation",),
        ),
        LiveRoundScript(
            11,
            "Customer message asset",
            "晚上继续。我准备在老客户群里发一段话，说我们下周会把阿姨服务标准和回访做得更清楚，也顺便带一下体验课。帮我写一版自然一点的群公告，放到 `outputs/老客户群公告.md`，别太营销，像老板本人发出来的就行。",
            ("asset",),
            ("outputs/老客户群公告.md",),
        ),
        LiveRoundScript(
            12,
            "Temporary hiring thought",
            "另外我临时又想到招聘一个兼职招生顾问，但现在现金流也不是特别宽裕。这个想法先不要影响主安排，你帮我列三个判断条件：什么情况下值得招，什么情况下先别招。请别默认招人一定能解决招生问题。",
            ("start_work",),
        ),
        LiveRoundScript(
            13,
            "Cash flow checkpoint",
            "回到门店经营这件事，我想把现金流也看一下。根据现有收入和支出，你帮我指出下个月最需要控制的一个花钱点，以及一个不能省过头的投入，最好能讲得让我这种不懂财务的人也明白，还能直接拿去跟会计沟通。",
            ("checkpoint",),
        ),
        LiveRoundScript(
            14,
            "Hiring decision",
            "关于兼职招生顾问这件事，别再模糊了。你帮我定一下这个月到底招不招，如果不招，那用什么替代办法；如果招，要先满足什么条件。请给一个明确判断，也说明这个判断以后在什么情况下需要改。我不想因为一时焦虑就多背固定开支。",
            ("decision",),
        ),
        LiveRoundScript(
            15,
            "Community event asset",
            "我们下周可能去社区做一场小活动，主题想围绕新手妈妈怎么挑月嫂，也顺便让别人知道我们这里能培训。帮我写一份活动小方案，放到 `outputs/社区活动小方案.md`，要简单、低成本、店员能执行，不要搞得像大型讲座。",
            ("asset",),
            ("outputs/社区活动小方案.md",),
        ),
        LiveRoundScript(
            16,
            "Update operating plan",
            "把收费选择、现金流注意点、社区活动安排都补进 `outputs/家政门店一个月经营安排.md`。如果原来安排里有太满的地方，你顺手帮我收一收，别让我下周看起来什么都要做。最后请让这个安排更像店里真实能执行的版本。",
            ("asset",),
            ("outputs/家政门店一个月经营安排.md",),
        ),
        LiveRoundScript(
            17,
            "Side threads pause",
            "直播和招聘这两个想法今天都先别展开了。你帮我各留一句以后再看时应该先问自己的问题，别让它们把主线带偏。这个只是方便我以后想起来，不需要变成今天的重点，也不要让店员以为明天就要开始做。",
            ("continuation",),
        ),
        LiveRoundScript(
            18,
            "Weekly review table",
            "我想让店员每天关店前花五分钟填一下今天做得怎么样，不要复杂表格。请帮我做一张下周复盘表，放到 `outputs/下周门店复盘表.md`，里面要能看出招生、培训、客户回访有没有推进，最好填完我一眼能看出问题。",
            ("asset",),
            ("outputs/下周门店复盘表.md",),
        ),
        LiveRoundScript(
            19,
            "Final weekly priorities decision",
            "如果我下周只能盯三件事，你帮我排个顺序。请考虑培训质量、客户信任、现金流和店员精力，不要为了好看列太多。我要的是明天早会能直接讲的版本，每件事最好都有一句为什么排在这里，以及谁最适合先负责。",
            ("decision",),
        ),
        LiveRoundScript(
            20,
            "Natural stop and next pickup",
            "今天先到这里。下次我回来，你要提醒我先看哪几个文件、先检查哪三个结果、如果情况变了应该先调整哪里。请用老板能看懂的话整理，别把过程讲复杂，也别让我重新翻所有聊天才能继续。",
            ("continuation",),
        ),
    )


def _novice_english_community_builder_rounds() -> tuple[LiveRoundScript, ...]:
    return (
        LiveRoundScript(
            1,
            "Community planning start",
            "I run a small local group for independent designers. Help me figure out what to focus on this month.",
            ("start_work",),
        ),
        LiveRoundScript(
            2,
            "Member signals",
            "Look at the notes and member feedback, then give me the two most useful things to improve first.",
            ("checkpoint",),
        ),
        LiveRoundScript(
            3,
            "Choose first move",
            "Which one should I do first? Pick one and explain the tradeoff in plain English.",
            ("decision",),
        ),
        LiveRoundScript(
            4,
            "Create run sheet",
            "Write a simple run sheet for the next event at `outputs/community-event-run-sheet.md`.",
            ("asset",),
            ("outputs/community-event-run-sheet.md",),
        ),
        LiveRoundScript(
            5,
            "Loose idea",
            "Side thought: maybe sponsors could help. Give me two rough sponsor ideas, but do not make this the main plan yet.",
            ("start_work",),
        ),
        LiveRoundScript(
            6,
            "Back to main",
            "Back to the monthly community plan. What is the one thing I should measure after the next event?",
            ("checkpoint",),
        ),
        LiveRoundScript(
            7,
            "Constraint check",
            "I only have three hours a week. Tighten the plan so it is realistic.",
            ("checkpoint",),
        ),
        LiveRoundScript(
            8,
            "Update run sheet",
            "Update `outputs/community-event-run-sheet.md` with the realistic version.",
            ("asset",),
            ("outputs/community-event-run-sheet.md",),
        ),
        LiveRoundScript(
            9,
            "Quick question",
            "Quick question: why should I not start three new event formats at once?",
            (),
        ),
        LiveRoundScript(
            10,
            "Natural stop",
            "I am done for today. Leave me a clean place to pick this up next time.",
            ("continuation",),
        ),
    )


def _mixed_complexity_rounds() -> tuple[LiveRoundScript, ...]:
    return (
        LiveRoundScript(
            1,
            "Start founder operating thread",
            "Start one durable long-cycle founder operating task about pricing, onboarding risk, and context continuity.",
            ("start_work",),
        ),
        LiveRoundScript(
            2,
            "First operating checkpoint",
            "Continue the founder operating task. Preserve a checkpoint with two priorities and one open risk.",
            ("checkpoint",),
        ),
        LiveRoundScript(
            3,
            "Short conceptual answer",
            "Quick answer only: why should durable task summaries stay concise?",
            (),
        ),
        LiveRoundScript(
            4,
            "Pricing guardrail decision",
            "Make a stable decision about the first pricing guardrail to test and preserve the reason.",
            ("decision",),
        ),
        LiveRoundScript(
            5,
            "Create operating brief asset",
            "Create `results/operating-brief.md` with the current operating brief and preserve it as an asset.",
            ("asset",),
            ("results/operating-brief.md",),
            (("results/operating-brief.md", "founder"),),
        ),
        LiveRoundScript(
            6,
            "Start temporary inbox tangent",
            "Start a temporary inbox thread for loose questions about onboarding language. Use `--persistence temporary` when preserving it.",
            ("start_work",),
        ),
        LiveRoundScript(
            7,
            "Temporary inbox checkpoint",
            "Continue the temporary inbox thread and preserve one lightweight checkpoint, without turning it into a formal project.",
            ("checkpoint",),
        ),
        LiveRoundScript(
            8,
            "Return to founder thread",
            "Return to the durable founder operating task and preserve a checkpoint about customer interview sequencing.",
            ("checkpoint",),
        ),
        LiveRoundScript(
            9,
            "Update operating brief asset",
            "Update `results/operating-brief.md` with the customer interview sequencing checkpoint and preserve the asset again.",
            ("asset",),
            ("results/operating-brief.md",),
            (("results/operating-brief.md", "founder"),),
        ),
        LiveRoundScript(
            10,
            "Founder handoff",
            "Preserve a handoff for the founder operating task before switching to a related implementation task.",
            ("continuation",),
        ),
        LiveRoundScript(
            11,
            "Start engineering continuity task",
            "Start a separate durable engineering task to inspect protocol continuity, runtime views, and asset indexing behavior.",
            ("start_work",),
        ),
        LiveRoundScript(
            12,
            "Engineering checkpoint",
            "Continue the engineering task and preserve a checkpoint with the most important implementation risk.",
            ("checkpoint",),
        ),
        LiveRoundScript(
            13,
            "Engineering scope decision",
            "Make a stable engineering decision about keeping runtime views rebuildable rather than canonical.",
            ("decision",),
        ),
        LiveRoundScript(
            14,
            "Create technical risk asset",
            "Create an engineering continuity task asset at `docs/technical-risk-note.md` with a compact risk note and preserve it.",
            ("asset",),
            ("docs/technical-risk-note.md",),
            (("docs/technical-risk-note.md", "protocol"),),
        ),
        LiveRoundScript(
            15,
            "Short sanity answer",
            "Quick answer only: what is one risk of letting runtime view failures block user work?",
            (),
        ),
        LiveRoundScript(
            16,
            "Resume founder after engineering",
            "Resume the founder operating task from Workroot continuity and preserve one checkpoint that incorporates the engineering risk.",
            ("checkpoint",),
        ),
        LiveRoundScript(
            17,
            "Temporary inbox handoff",
            "Resume the temporary inbox thread and preserve a handoff so the loose onboarding-language discussion can continue later.",
            ("continuation",),
        ),
        LiveRoundScript(
            18,
            "Interview segment decision",
            "Return to the founder operating task and make a stable decision about the next customer interview segment.",
            ("decision",),
        ),
        LiveRoundScript(
            19,
            "Customer interview plan asset",
            "Create a founder operating task asset at `results/customer-interview-plan.md` with a short interview plan and preserve it.",
            ("asset",),
            ("results/customer-interview-plan.md",),
            (("results/customer-interview-plan.md", "founder"),),
        ),
        LiveRoundScript(
            20,
            "Founder continuity handoff",
            "Preserve a clear founder operating handoff with current state, next action, and one open item.",
            ("continuation",),
        ),
        LiveRoundScript(
            21,
            "Start metrics investigation",
            "Start a third durable investigation task to connect `metrics.csv` signals to task continuity and asset recall quality.",
            ("start_work",),
        ),
        LiveRoundScript(
            22,
            "Metrics checkpoint",
            "Continue the metrics investigation and preserve a checkpoint with the strongest signal and one caveat.",
            ("checkpoint",),
        ),
        LiveRoundScript(
            23,
            "Metrics decision",
            "Make a stable decision about which metric should drive the next validation pass.",
            ("decision",),
        ),
        LiveRoundScript(
            24,
            "Research synthesis asset",
            "Create `reports/research-synthesis.md` with the metrics synthesis and preserve it as an asset.",
            ("asset",),
            ("reports/research-synthesis.md",),
            (("reports/research-synthesis.md", "metrics"),),
        ),
        LiveRoundScript(
            25,
            "Short contrast answer",
            "Quick answer only: contrast a task checkpoint with a user-visible asset in one sentence.",
            (),
        ),
        LiveRoundScript(
            26,
            "Resume engineering with evidence",
            "Resume the engineering continuity task and preserve a checkpoint about whether FTS and runtime views are enough for inspection.",
            ("checkpoint",),
        ),
        LiveRoundScript(
            27,
            "Short implementation answer",
            "Quick answer only: what should the next agent inspect first if a runtime view directory is empty?",
            (),
        ),
        LiveRoundScript(
            28,
            "Resume founder final synthesis",
            "Resume the founder operating task and preserve a checkpoint that links pricing, interviews, and engineering continuity risk.",
            ("checkpoint",),
        ),
        LiveRoundScript(
            29,
            "Final cross-task handoff",
            "Preserve a final handoff that tells the next agent how to continue across the founder, engineering, and metrics tasks.",
            ("continuation",),
        ),
        LiveRoundScript(
            30,
            "Executive summary asset",
            "Create `results/executive-summary.md` with the final cross-task summary and preserve it as an asset.",
            ("asset",),
            ("results/executive-summary.md",),
            (("results/executive-summary.md", "workroot"),),
        ),
    )


def _all_expected_asset_paths(role: LiveRoleScenario) -> tuple[str, ...]:
    paths: list[str] = []
    for round_script in role.rounds:
        for path in round_script.expected_asset_paths:
            if path not in paths:
                paths.append(path)
    return tuple(paths)


def _role_requires_continuity_view(role: LiveRoleScenario) -> bool:
    return any(
        shape in {"checkpoint", "continuation", "asset", "decision"}
        for round_script in role.rounds
        for shape in round_script.expected_shapes
    )


def _workroot_record(*, ai_home: Path, workroot_id: str) -> dict[str, str]:
    for record in list_workroots(ai_workroot_home=ai_home):
        if record["workrootId"] == workroot_id:
            return record
    raise ValueError(f"missing Workroot record: {workroot_id}")


def _count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _count_where(conn: sqlite3.Connection, table: str, where: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}").fetchone()[0])


def _group_count(conn: sqlite3.Connection, table: str, column: str) -> dict[str, int]:
    rows = conn.execute(f"SELECT {column}, COUNT(*) FROM {table} GROUP BY {column}").fetchall()
    return {str(row[0]): int(row[1]) for row in rows}


def _tasks(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        {
            "taskId": row[0],
            "title": row[1],
            "status": row[2],
            "role": row[3],
            "processLevel": row[4],
            "summaryId": row[5],
        }
        for row in conn.execute(
            """
            SELECT task_id, title, status, role, process_level, summary_id
            FROM tasks
            ORDER BY created_at, task_id
            """
        ).fetchall()
    ]


def _task_runs(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        {"runId": row[0], "taskId": row[1], "status": row[2], "goal": row[3]}
        for row in conn.execute(
            """
            SELECT run_id, task_id, status, goal
            FROM task_runs
            ORDER BY started_at, run_id
            """
        ).fetchall()
    ]


def _asset_paths(conn: sqlite3.Connection) -> list[str]:
    return [
        str(row[0])
        for row in conn.execute(
            "SELECT current_path FROM assets WHERE current_path IS NOT NULL ORDER BY current_path"
        ).fetchall()
    ]


def _asset_owners(conn: sqlite3.Connection) -> dict[str, list[str]]:
    owners = {path: [] for path in _asset_paths(conn)}
    rows = conn.execute(
        """
        SELECT a.current_path, t.title
        FROM assets a
        JOIN relationship_nodes asset_node
          ON asset_node.workroot_id = a.workroot_id
         AND asset_node.target_type = 'asset'
         AND asset_node.target_id = a.asset_id
        JOIN relationship_edges edge
          ON edge.workroot_id = a.workroot_id
         AND edge.to_node_id = asset_node.node_id
         AND COALESCE(edge.status, 'active') = 'active'
        JOIN relationship_nodes task_node
          ON task_node.workroot_id = a.workroot_id
         AND task_node.node_id = edge.from_node_id
         AND task_node.target_type = 'task'
        JOIN tasks t
          ON t.workroot_id = a.workroot_id
         AND t.task_id = task_node.target_id
        WHERE a.current_path IS NOT NULL
        ORDER BY a.current_path, t.title
        """
    ).fetchall()
    for path, title in rows:
        owners.setdefault(str(path), []).append(str(title))
    return owners


def _latest_handoff(conn: sqlite3.Connection) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT h.handoff_id, h.task_id, h.run_id, t.title, t.role, h.current_state, h.next_action
        FROM handoffs h
        LEFT JOIN tasks t ON t.workroot_id = h.workroot_id AND t.task_id = h.task_id
        WHERE h.status = 'current'
        ORDER BY h.created_at DESC, h.handoff_id DESC
        LIMIT 1
        """
    ).fetchone()
    if row is None:
        return None
    return {
        "handoffId": row[0],
        "taskId": row[1],
        "runId": row[2],
        "taskTitle": row[3],
        "taskRole": row[4],
        "currentState": row[5],
        "nextAction": row[6],
    }


def _task_proliferation(conn: sqlite3.Connection) -> dict[str, int]:
    active_roots = _count_where(
        conn,
        "tasks",
        """
        role = 'normal'
        AND process_level = 'L1'
        AND COALESCE(status, 'active') IN ('active', 'paused', 'blocked')
        AND (parent_task_id IS NULL OR parent_task_id = '')
        """,
    )
    duplicate_titles = 0
    rows = conn.execute(
        """
        SELECT LOWER(TRIM(title)), COUNT(*)
        FROM tasks
        WHERE title IS NOT NULL AND TRIM(title) != ''
          AND COALESCE(status, 'active') IN ('active', 'paused', 'blocked')
        GROUP BY LOWER(TRIM(title))
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    for _title, count in rows:
        duplicate_titles += int(count) - 1
    return {"activeNormalRootTasks": active_roots, "duplicateTitleCount": duplicate_titles}


def _status_delta(
    db_summary: dict[str, Any],
    before_db_summary: dict[str, Any] | None,
    status: str,
) -> int:
    after = int((db_summary.get("protocolEventStatuses") or {}).get(status, 0))
    before = int(((before_db_summary or {}).get("protocolEventStatuses") or {}).get(status, 0))
    return max(0, after - before)


def _runtime_view_directories(state_directory: Path) -> dict[str, int]:
    directories = ("state", "tasks", "handoffs", "assets", "relationships", "indexes", "context", "diagnostics")
    return {name: _count_files(state_directory / name) for name in directories}


def _runtime_file_count(state_directory: Path) -> int:
    return sum(_runtime_view_directories(state_directory).values())


def _count_files(directory: Path) -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for path in directory.rglob("*") if path.is_file())


def _normalize_relative_path(value: str) -> str:
    return value.replace("\\", "/").strip("/")
