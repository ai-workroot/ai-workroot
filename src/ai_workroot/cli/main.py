"""Thin CLI entry point for AI Workroot."""

from __future__ import annotations

import argparse
from collections.abc import Sequence


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
        subparsers.add_parser(command, help=f"{command} command placeholder")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print("AI Workroot 0.9.530")
        return 0

    if args.command:
        parser.error(f"`{args.command}` is not implemented in the new package yet")

    parser.print_help()
    return 0
