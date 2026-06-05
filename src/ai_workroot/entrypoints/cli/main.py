"""Thin CLI entry point for AI Workroot."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import uuid

from ai_workroot.commands.agent_exchange import (
    COMMIT_SHAPES,
    SYNC_REASON_CHOICES,
    run_commit_request,
    run_commit_shape,
    run_exchange_request,
    render_agent_response,
    run_sync_request,
)
from ai_workroot.commands.bootstrap_dev import bootstrap_dev
from ai_workroot.commands.build_context import build_context
from ai_workroot.commands.init_workroot import initialize_workroot, rollback_initialized_workroot
from ai_workroot.commands.list_workroots import list_workroots
from ai_workroot.commands.run_doctor import run_doctor, run_release_doctor
from ai_workroot.commands.show_status import find_workroot_by_cwd
from ai_workroot.entrypoints.native_agent.native import sync_native_agent_entry


PRIMARY_COMMANDS = ("init", "list", "status", "context", "doctor", "bootstrap-dev", "agent")
COMMAND_HELP = {
    "init": "Register a Clean Workroot directory.",
    "list": "List registered Workroots.",
    "status": "Show Workroot status for a directory.",
    "context": "Render an agent context package.",
    "doctor": "Run read-only system health checks.",
    "bootstrap-dev": "Bootstrap this source repo for dogfood development.",
    "agent": "Exchange Workroot Agent Protocol messages.",
}


class CleanHelpFormatter(argparse.HelpFormatter):
    def add_arguments(self, actions: Sequence[argparse.Action]) -> None:
        visible_actions: list[argparse.Action] = []
        for action in actions:
            if isinstance(action, argparse._SubParsersAction):  # type: ignore[attr-defined]
                action._choices_actions = [  # type: ignore[attr-defined]
                    choice
                    for choice in action._choices_actions
                    if choice.help is not argparse.SUPPRESS  # type: ignore[attr-defined]
                ]
            if action.help is not argparse.SUPPRESS:
                visible_actions.append(action)
        super().add_arguments(visible_actions)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="workroot",
        description="AI Workroot Clean Workroot command line interface.",
        formatter_class=CleanHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show the AI Workroot version and exit.",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="command")
    for command in PRIMARY_COMMANDS:
        command_parser = subparsers.add_parser(command, help=COMMAND_HELP[command])
        if command == "init":
            command_parser.add_argument("--name", required=True)
            command_parser.add_argument("--directory", required=True)
            command_parser.add_argument("--id", dest="workroot_id")
            native_entry = command_parser.add_mutually_exclusive_group()
            native_entry.add_argument("--native-agent-entry", action="store_true")
            native_entry.add_argument("--no-native-agent-entry", action="store_true")
        if command == "list":
            command_parser.add_argument("--format", choices=("text", "json"), default="text")
        if command == "status":
            command_parser.add_argument("--cwd", default=".")
        if command == "context":
            command_parser.add_argument("--agent", choices=("codex", "claude"), required=True)
            command_parser.add_argument("--cwd", default=".")
            command_parser.add_argument("--query", default="")
            command_parser.add_argument("--mode", choices=("fast", "standard", "quality", "deep"), default="standard")
            command_parser.add_argument("--target-tokens", type=int)
            command_parser.add_argument("--hard-token-limit", type=int)
            command_parser.add_argument("--debug", action="store_true")
        if command == "doctor":
            command_parser.add_argument("--cwd", default=".")
            command_parser.add_argument("--release", action="store_true")
        if command == "bootstrap-dev":
            command_parser.add_argument(
                "--dry-run", action="store_true", help="Validate bootstrap-dev inputs without writes."
            )
            command_parser.add_argument("--cwd", default=".", help="Repository directory to bootstrap.")
        if command == "agent":
            agent_subparsers = command_parser.add_subparsers(dest="agent_command", metavar="agent-command")
            exchange_parser = agent_subparsers.add_parser("exchange", help="Run a sync or commit envelope.")
            exchange_parser.add_argument("--request", required=True, help="Path to an exchange envelope JSON file.")
            exchange_parser.add_argument("--format", choices=("json", "guidance", "packet"), default="json")

            sync_parser = agent_subparsers.add_parser("sync", help="Create a protocol sync request.")
            sync_parser.add_argument("--request-id")
            sync_parser.add_argument("--agent", default="codex")
            sync_parser.add_argument("--cwd", default=".")
            sync_parser.add_argument("--workroot-id")
            sync_parser.add_argument("--reason", choices=SYNC_REASON_CHOICES, default="before_work")
            sync_parser.add_argument("--query", default="")
            sync_parser.add_argument("--known-state", default="{}")
            sync_parser.add_argument("--work-signal", "--signal", dest="work_signal", default="{}")
            sync_parser.add_argument("--phase")
            sync_parser.add_argument("--work-kind")
            sync_parser.add_argument("--intended-action")
            sync_parser.add_argument("--focus")
            sync_parser.add_argument("--concern", action="append", default=[])
            sync_parser.add_argument("--persistence", choices=("normal", "temporary", "quick"), help=argparse.SUPPRESS)
            sync_parser.add_argument("--format", choices=("json", "guidance", "packet"), default="json")
            sync_parser.add_argument("work_signal_parts", nargs="*", help=argparse.SUPPRESS)

            commit_parser = agent_subparsers.add_parser("commit", help="Commit a protocol event batch.")
            commit_parser.add_argument("--request", help="Path to a commit request JSON file.")
            commit_parser.add_argument(
                "--shape",
                choices=_commit_shape_choices(),
                help="LLM-facing commit shape.",
            )
            commit_parser.add_argument("--lease", help="Exchange lease id for commit.")
            commit_parser.add_argument("--agent", default="codex")
            commit_parser.add_argument("--cwd")
            commit_parser.add_argument("--workroot-id")
            commit_parser.add_argument("--title", default="")
            commit_parser.add_argument("--summary", default="")
            commit_parser.add_argument("--current-state", default="")
            commit_parser.add_argument("--next-action", default="")
            commit_parser.add_argument("--state", dest="current_state")
            commit_parser.add_argument("--next", dest="next_action")
            commit_parser.add_argument("--task-id")
            commit_parser.add_argument("--run-id")
            commit_parser.add_argument("--parent-task-id")
            commit_parser.add_argument("--persistence", choices=("normal", "temporary", "quick"), default="normal")
            commit_parser.add_argument("--done", action="append", default=[])
            commit_parser.add_argument("--open", action="append", default=[])
            commit_parser.add_argument("--blocked", action="append", default=[])
            commit_parser.add_argument(
                "--changed-steps-or-results", "--changed-step-or-result", action="append", default=[]
            )
            commit_parser.add_argument("--target")
            commit_parser.add_argument("--target-ref")
            commit_parser.add_argument("--change", "--state-change", dest="change")
            commit_parser.add_argument("--path", default="")
            commit_parser.add_argument("--asset-kind", default="")
            commit_parser.add_argument("--status", default="")
            commit_parser.add_argument("--decision", default="")
            commit_parser.add_argument("--reason-text", default="")
            commit_parser.add_argument("--scope", default="")
            commit_parser.add_argument("--session-id")
            commit_parser.add_argument("--event-id")
            commit_parser.add_argument("--request-id")
            commit_parser.add_argument("--idempotency-key")
            commit_parser.add_argument("--occurred-at")
            commit_parser.add_argument("--format", choices=("json", "guidance", "packet"), default="json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print("AI Workroot 0.9.531")
        return 0

    if args.command == "init":
        result = None
        try:
            result = initialize_workroot(
                name=args.name,
                directory=Path(args.directory),
                workroot_id=args.workroot_id,
            )
            if args.native_agent_entry:
                try:
                    _sync_native_agent_entries(Path(args.directory))
                except (OSError, ValueError) as entry_exc:
                    try:
                        rollback_initialized_workroot(result)
                    except (OSError, ValueError) as cleanup_exc:
                        parser.exit(
                            1,
                            (
                                f"{entry_exc}\n"
                                "warning: cleanup after Native Agent Entry failure also failed: "
                                f"{cleanup_exc}\n"
                            ),
                        )
                    raise
        except (OSError, ValueError) as exc:
            parser.exit(1, f"{exc}\n")
        for warning in result.warnings:
            print(warning, file=__import__("sys").stderr)
        if args.native_agent_entry:
            print(f"initialized {result.registration.workroot_id} agent-ready")
        else:
            print(result.message())
        return 0

    if args.command == "list":
        records = list_workroots()
        if args.format == "json":
            print(json.dumps(records, ensure_ascii=False, indent=2))
        else:
            for record in records:
                print(f"{record['workrootId']}\t{record['name']}\t{record['userDirectory']}")
        return 0

    if args.command == "status":
        try:
            record = find_workroot_by_cwd(Path(args.cwd))
        except ValueError as exc:
            parser.exit(1, f"{exc}\n")
        print(f"Workroot: {record['name']} ({record['workrootId']})")
        print(f"UserDirectory: {record['userDirectory']}")
        print(f"StateDirectory: {record['stateDirectory']}")
        return 0

    if args.command == "context":
        try:
            package = build_context(
                agent=args.agent,
                cwd=Path(args.cwd),
                query=args.query,
                mode=args.mode,
                target_tokens=args.target_tokens,
                hard_token_limit=args.hard_token_limit,
                debug=args.debug,
            )
        except (OSError, ValueError) as exc:
            parser.exit(1, f"{exc}\n")
        print(package, end="")
        return 0

    if args.command == "doctor":
        result = run_release_doctor(Path(args.cwd)) if args.release else run_doctor(cwd=Path(args.cwd))
        if args.release:
            print(result.render_text().replace("AI Workroot doctor:", "AI Workroot release doctor:"), end="")
        else:
            print(result.render_text(), end="")
        return 0 if result.status == "PASS" else 1

    if args.command == "bootstrap-dev":
        try:
            result = bootstrap_dev(Path(args.cwd), dry_run=args.dry_run)
            if not args.dry_run:
                _sync_native_agent_entries(Path(result.user_directory))
        except (OSError, ValueError) as exc:
            parser.exit(1, f"{exc}\n")
        print(result.message())
        return 0

    if args.command == "agent":
        if not args.agent_command:
            parser.error("agent requires a subcommand")
        try:
            if args.agent_command == "exchange":
                response = run_exchange_request(Path(args.request))
            elif args.agent_command == "sync":
                response = run_sync_request(
                    request_id=args.request_id or f"req-{uuid.uuid4().hex}",
                    agent_name=args.agent,
                    cwd=Path(args.cwd),
                    workroot_id=args.workroot_id,
                    query=args.query,
                    reason=args.reason,
                    known_state=_json_object_arg(args.known_state, "--known-state"),
                    work_signal=_sync_work_signal(
                        _merge_split_work_signal_args(
                            _json_object_arg(args.work_signal, "--work-signal"),
                            phase=args.phase,
                            work_kind=args.work_kind,
                            intended_action=args.intended_action,
                            focus=args.focus,
                            concerns=tuple(args.concern),
                            work_signal_parts=tuple(args.work_signal_parts),
                        ),
                        persistence=args.persistence,
                    ),
                )
            elif args.agent_command == "commit":
                if args.request:
                    response = run_commit_request(Path(args.request))
                elif args.shape:
                    response = run_commit_shape(
                        shape=args.shape,
                        lease_id=args.lease or "",
                        agent_name=args.agent,
                        cwd=Path(args.cwd) if args.cwd else None,
                        workroot_id=args.workroot_id,
                        title=args.title,
                        summary=args.summary,
                        current_state=args.current_state,
                        next_action=args.next_action,
                        task_id=args.task_id or _task_id_from_target_ref(args.target_ref),
                        run_id=args.run_id,
                        parent_task_id=args.parent_task_id,
                        persistence=args.persistence,
                        done=(*tuple(args.done), *tuple(args.changed_steps_or_results)),
                        open=tuple(args.open),
                        blocked=tuple(args.blocked),
                        target=args.target or args.target_ref,
                        change=args.change,
                        path=args.path,
                        asset_kind=args.asset_kind,
                        status=args.status,
                        decision=args.decision,
                        reason_text=args.reason_text,
                        scope=args.scope,
                        session_id=args.session_id,
                        event_id=args.event_id,
                        request_id=args.request_id,
                        idempotency_key=args.idempotency_key,
                        occurred_at=args.occurred_at,
                    )
                else:
                    parser.error("agent commit requires --request or --shape")
            else:
                parser.error(f"`agent {args.agent_command}` is not implemented")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            parser.exit(1, f"{exc}\n")
        print(render_agent_response(response, output_format=args.format, agent=getattr(args, "agent", "codex")), end="")
        return 0

    if args.command:
        parser.error(f"`{args.command}` is not implemented in the new package yet")

    parser.print_help()
    return 0


def _sync_native_agent_entries(directory: Path) -> None:
    paths = (directory / "AGENTS.md", directory / "CLAUDE.md")
    snapshots = {path: path.read_text(encoding="utf-8") if path.exists() else None for path in paths}
    try:
        sync_native_agent_entry(directory / "AGENTS.md", "codex")
        sync_native_agent_entry(directory / "CLAUDE.md", "claude")
    except (OSError, ValueError) as entry_exc:
        try:
            _restore_native_agent_entry_snapshots(snapshots)
        except (OSError, ValueError) as restore_exc:
            raise ValueError(
                f"{entry_exc}\nwarning: cleanup after Native Agent Entry partial write also failed: {restore_exc}"
            ) from entry_exc
        raise


def _restore_native_agent_entry_snapshots(snapshots: dict[Path, str | None]) -> None:
    for path, content in snapshots.items():
        if content is None:
            if path.exists():
                path.unlink()
        else:
            path.write_text(content, encoding="utf-8")


def _json_object_arg(raw: str, label: str) -> dict[str, object]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        text = str(raw or "").strip()
        if label == "--work-signal":
            inferred = _plain_text_work_signal(text)
            if inferred:
                return inferred
        return {"note": text} if text else {}
    if not isinstance(value, dict):
        return {"note": str(value)}
    return value


def _task_id_from_target_ref(target_ref: str | None) -> str | None:
    value = str(target_ref or "").strip()
    if not value:
        return None
    if value.startswith("task:"):
        value = value.split(":", 1)[1].strip()
    if value.startswith(("task-", "task_")):
        return value
    return None


def _commit_shape_choices() -> tuple[str, ...]:
    choices: list[str] = []
    for shape in COMMIT_SHAPES:
        for value in (shape, shape.replace("_", "-")):
            if value not in choices:
                choices.append(value)
    return tuple(choices)


def _sync_work_signal(work_signal: dict[str, object], *, persistence: str | None) -> dict[str, object]:
    signal = dict(work_signal)
    if not persistence or signal.get("work_kind"):
        return signal
    if persistence == "quick":
        signal.setdefault("work_kind", "quick")
        signal.setdefault("intended_action", "answer")
        return signal
    if persistence == "temporary":
        signal.setdefault("work_kind", "inbox")
        signal.setdefault("phase", "switching")
        signal.setdefault("intended_action", "preserve")
        return signal
    signal.setdefault("work_kind", "task")
    signal.setdefault("phase", "switching")
    signal.setdefault("intended_action", "plan")
    return signal


def _merge_split_work_signal_args(
    work_signal: dict[str, object],
    *,
    phase: str | None,
    work_kind: str | None,
    intended_action: str | None,
    focus: str | None,
    concerns: tuple[str, ...],
    work_signal_parts: tuple[str, ...] = (),
) -> dict[str, object]:
    signal = dict(work_signal)
    if work_signal_parts:
        signal.update(_plain_text_key_value_work_signal(", ".join(work_signal_parts)))
    if phase:
        signal["phase"] = phase
    if work_kind:
        signal["work_kind"] = work_kind
    if intended_action:
        signal["intended_action"] = intended_action
    if focus:
        signal["focus"] = focus
    if concerns:
        existing = signal.get("concerns")
        merged = [str(item) for item in existing] if isinstance(existing, list) else []
        merged.extend(concerns)
        signal["concerns"] = merged
    return signal


def _plain_text_work_signal(text: str) -> dict[str, object]:
    lowered = text.lower().strip()
    if not lowered:
        return {}
    key_value_signal = _plain_text_key_value_work_signal(text)
    if key_value_signal:
        return key_value_signal
    if lowered in {"new_work", "new work", "start work", "start task"}:
        return {"work_kind": "task", "intended_action": "plan", "phase": "switching", "focus": text}
    if lowered == "quick":
        return {"work_kind": "quick", "intended_action": "answer", "focus": text}
    if lowered == "continuation":
        return {"work_kind": "continuation", "intended_action": "preserve", "focus": text}
    if lowered == "inbox":
        return {"work_kind": "inbox", "intended_action": "preserve", "focus": text}
    if lowered == "decision":
        return {"work_kind": "decision", "intended_action": "decide", "focus": text}
    if lowered == "review":
        return {"work_kind": "review", "intended_action": "review", "focus": text}
    if lowered == "asset":
        return {"work_kind": "authoring", "intended_action": "preserve", "focus": text}
    if lowered == "handoff":
        return {"work_kind": "continuation", "intended_action": "preserve", "focus": text}
    return {"focus": text}


def _plain_text_key_value_work_signal(text: str) -> dict[str, object]:
    allowed_keys = {"phase", "work_kind", "intended_action", "focus", "concerns"}
    parts = [part.strip() for part in text.replace(";", ",").split(",") if part.strip()]
    if not parts or any("=" not in part for part in parts):
        return {}
    signal: dict[str, object] = {}
    for part in parts:
        key, value = part.split("=", 1)
        normalized_key = key.strip().replace("-", "_")
        if normalized_key not in allowed_keys:
            continue
        cleaned_value = value.strip().strip("\"'")
        if normalized_key == "concerns":
            signal[normalized_key] = [item.strip() for item in cleaned_value.replace("|", " ").split() if item.strip()]
        elif cleaned_value:
            signal[normalized_key] = cleaned_value
    return signal
