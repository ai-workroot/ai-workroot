"""Thin CLI entry point for AI Workroot."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from ai_workroot.runtime.bootstrap import bootstrap_dev


PRIMARY_COMMANDS = ("init", "list", "status", "context", "doctor", "bootstrap-dev")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="workroot",
        description="AI Workroot Clean Workroot command line interface.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show the AI Workroot version and exit.",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="command")
    for command in PRIMARY_COMMANDS:
        command_parser = subparsers.add_parser(command, help=f"{command} command placeholder")
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
