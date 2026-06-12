"""Explicit opt-in runner for AI Workroot end-to-end suites."""

from __future__ import annotations

import argparse
import os
import unittest
from pathlib import Path

from tests.e2e.safety import E2E_RUNNER_ACTIVE_ENV, default_sandbox_base, new_default_run_root, require_e2e_opt_in


SUITES = {
    "safety": "tests.e2e.safety_cases",
    "persona-smoke": "tests.e2e.persona_smoke_cases",
    "longrun": "tests.e2e.longrun_cases",
    "live-agent": "tests.e2e.live_agent_cases",
    "live-protocol": "tests.e2e.live_protocol_cases",
    "live-task-continuity": "tests.e2e.live_task_continuity_cases",
}
REMOTE_LLM_SUITES = {"live-agent", "live-protocol", "live-task-continuity"}
REMOTE_LLM_SUITE_LABELS = {
    "live-agent": "Live-agent",
    "live-protocol": "Live-protocol",
    "live-task-continuity": "Live-task-continuity",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="List available E2E suites.")
    parser.add_argument("--suite", choices=sorted(SUITES), action="append", help="E2E suite to run. May be repeated.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate opt-in and print selected suites without running them."
    )
    parser.add_argument(
        "--sandbox-base", help="Sandbox base for preserved run roots. Defaults to ~/tmp/ai-workroot-e2e-sandboxes."
    )
    parser.add_argument("--run-root", help="Explicit run-* root under the sandbox base.")
    parser.add_argument(
        "--rounds",
        type=int,
        help="Round count for live-task-continuity. Accepted range is validated by the suite.",
    )
    parser.add_argument(
        "--role",
        help="Single role slug for live-task-continuity, e.g. live-founder-operator.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not require_e2e_opt_in():
        return 2

    if args.list:
        for name in sorted(SUITES):
            print(name)
        return 0

    sandbox_base = Path(args.sandbox_base).expanduser().resolve() if args.sandbox_base else default_sandbox_base()
    run_root = Path(args.run_root).expanduser().resolve() if args.run_root else new_default_run_root(base=sandbox_base)
    selected = args.suite or []
    if not selected:
        parser.error("choose at least one --suite or use --list")
    remote_suites = sorted(set(selected) & REMOTE_LLM_SUITES)
    if remote_suites and os.environ.get("AI_WORKROOT_E2E_ALLOW_REMOTE_LLM") != "1":
        joined = ", ".join(REMOTE_LLM_SUITE_LABELS[name] for name in remote_suites)
        print(f"{joined} E2E requires AI_WORKROOT_E2E_ALLOW_REMOTE_LLM=1.", file=__import__("sys").stderr)
        return 2

    if args.dry_run:
        print("Selected E2E suites:")
        for name in selected:
            print(f"- {name}")
        if args.rounds is not None:
            print(f"Rounds: {args.rounds}")
        if args.role:
            print(f"Role: {args.role}")
        print(f"Sandbox run root: {run_root}")
        return 0

    os.environ["AI_WORKROOT_E2E_RUN_ROOT"] = str(run_root)
    os.environ["AI_WORKROOT_E2E_SANDBOX_BASE"] = str(sandbox_base)
    os.environ[E2E_RUNNER_ACTIVE_ENV] = "1"
    if args.rounds is not None:
        os.environ["AI_WORKROOT_E2E_LIVE_TASK_ROUNDS"] = str(args.rounds)
    if args.role:
        os.environ["AI_WORKROOT_E2E_LIVE_TASK_ROLE"] = str(args.role)
    repo_root = Path(__file__).resolve().parents[2]
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    for name in selected:
        suite.addTests(loader.loadTestsFromName(SUITES[name]))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        return 1
    print(f"E2E reports are written under {run_root}")
    print(f"Repository: {repo_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
