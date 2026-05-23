"""Explicit opt-in runner for AI Workroot end-to-end suites."""

from __future__ import annotations

import argparse
import os
import unittest
from pathlib import Path

from tests.e2e.safety import default_sandbox_base, new_default_run_root, require_e2e_opt_in


SUITES = {
    "safety": "tests.e2e.safety_cases",
    "persona-smoke": "tests.e2e.persona_smoke_cases",
    "longrun": "tests.e2e.longrun_cases",
    "live-agent": "tests.e2e.live_agent_cases",
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
    if "live-agent" in selected and os.environ.get("AI_WORKROOT_E2E_ALLOW_REMOTE_LLM") != "1":
        print("Live-agent E2E requires AI_WORKROOT_E2E_ALLOW_REMOTE_LLM=1.", file=__import__("sys").stderr)
        return 2

    if args.dry_run:
        print("Selected E2E suites:")
        for name in selected:
            print(f"- {name}")
        print(f"Sandbox run root: {run_root}")
        return 0

    os.environ["AI_WORKROOT_E2E_RUN_ROOT"] = str(run_root)
    os.environ["AI_WORKROOT_E2E_SANDBOX_BASE"] = str(sandbox_base)
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
