"""Thin CLI entry point for AI Workroot."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
from pathlib import Path

from ai_workroot.runtime.bootstrap import bootstrap_dev
from ai_workroot.runtime.context import ContextRequest, build_context_package
from ai_workroot.runtime.doctor import run_doctor, run_release_doctor
from ai_workroot.runtime.environment import load_context_control_config
from ai_workroot.runtime.init import initialize_workroot
from ai_workroot.runtime.paths import resolve_ai_workroot_home
from ai_workroot.runtime.registry import find_workroot_by_cwd, list_workroots


PRIMARY_COMMANDS = ("init", "list", "status", "context", "doctor", "bootstrap-dev")
COMMAND_HELP = {
    "init": "Register a Clean Workroot directory.",
    "list": "List registered Workroots.",
    "status": "Show Workroot status for a directory.",
    "context": "Render an agent context package.",
    "doctor": "Run read-only system health checks.",
    "bootstrap-dev": "Bootstrap this source repo for dogfood development.",
}


class CleanHelpFormatter(argparse.HelpFormatter):
    def add_arguments(self, actions: Sequence[argparse.Action]) -> None:
        visible_actions: list[argparse.Action] = []
        for action in actions:
            if isinstance(action, argparse._SubParsersAction):  # type: ignore[attr-defined]
                action._choices_actions = [  # type: ignore[attr-defined]
                    choice for choice in action._choices_actions if choice.help is not argparse.SUPPRESS  # type: ignore[attr-defined]
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
            command_parser.add_argument("--dry-run", action="store_true", help="Validate bootstrap-dev inputs without writes.")
            command_parser.add_argument("--cwd", default=".", help="Repository directory to bootstrap.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print("AI Workroot 0.9.530")
        return 0

    if args.command == "init":
        try:
            result = initialize_workroot(
                name=args.name,
                directory=Path(args.directory),
                workroot_id=args.workroot_id,
                native_agent_entry=args.native_agent_entry,
            )
        except ValueError as exc:
            parser.exit(1, f"{exc}\n")
        for warning in result.warnings:
            print(warning, file=__import__("sys").stderr)
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
        config = load_context_control_config(resolve_ai_workroot_home())
        target_tokens = args.target_tokens if args.target_tokens is not None else config.default_target_tokens
        hard_token_limit = args.hard_token_limit if args.hard_token_limit is not None else config.default_hard_token_limit
        budget_source = "cli" if args.target_tokens is not None or args.hard_token_limit is not None else "config"
        if target_tokens <= 0 or hard_token_limit <= 0 or target_tokens > hard_token_limit:
            parser.exit(1, "invalid context token budget\n")
        try:
            package = build_context_package(
                ContextRequest(
                    agent=args.agent,
                    cwd=Path(args.cwd),
                    query=args.query,
                    mode=args.mode,
                    target_tokens=target_tokens,
                    hard_token_limit=hard_token_limit,
                    debug=args.debug,
                    budget_source=budget_source,
                )
            )
        except ValueError as exc:
            parser.exit(1, f"{exc}\n")
        print(package, end="")
        return 0

    if args.command == "doctor":
        result = run_release_doctor(Path.cwd()) if args.release else run_doctor(cwd=Path(args.cwd))
        if args.release:
            print(result.render_text().replace("AI Workroot doctor:", "AI Workroot release doctor:"), end="")
        else:
            print(result.render_text(), end="")
        return 0 if result.status == "PASS" else 1

    if args.command == "bootstrap-dev":
        try:
            result = bootstrap_dev(Path(args.cwd), dry_run=args.dry_run)
        except ValueError as exc:
            parser.exit(1, f"{exc}\n")
        print(result.message())
        return 0

    if args.command:
        parser.error(f"`{args.command}` is not implemented in the new package yet")

    parser.print_help()
    return 0
