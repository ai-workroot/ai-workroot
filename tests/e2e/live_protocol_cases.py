from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.e2e.harness import env_for, run_cli
from tests.e2e.live_protocol import (
    WORKROOT_ID,
    build_codex_command,
    classify_protocol_discovery,
    classify_workroot_commands,
    create_workroot_command_wrapper,
    run_continuation_from_handoff,
    run_degraded_commit_case,
    run_discovery_diagnostic,
    run_guided_minimal_loop,
    summarize_workroot_database,
    write_live_protocol_summary,
)
from tests.e2e.safety import new_default_run_root, prepare_run_root, require_e2e_runner_active


class LiveProtocolHarnessTest(unittest.TestCase):
    def test_wrapper_logs_command_and_executes_workroot_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox_base = Path(tmp) / "sandboxes"
            run_root = prepare_run_root(new_default_run_root(base=sandbox_base), sandbox_base=sandbox_base)
            ai_home = run_root / "ai-workroot-home"
            env = env_for(ai_home)
            user_dir = run_root / "user-dirs" / "live-protocol"
            user_dir.mkdir(parents=True)
            init = run_cli(
                (
                    "init",
                    "--name",
                    "Live Protocol",
                    "--directory",
                    str(user_dir),
                    "--id",
                    WORKROOT_ID,
                    "--native-agent-entry",
                ),
                env=env,
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            log_path = run_root / "transcripts" / "live-protocol" / "wrapper-log.jsonl"
            wrapper = create_workroot_command_wrapper(run_root=run_root, command_log_path=log_path)

            completed = subprocess.run(
                (str(wrapper), "status", "--cwd", "."),
                cwd=user_dir,
                env={**env, "WORKROOT_COMMAND_LOG": str(log_path)},
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(records[0]["argv"], ["status", "--cwd", "."])
            self.assertEqual(records[0]["returncode"], 0)

    def test_wrapper_bin_directory_is_owned_for_next_sandbox_reset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox_base = Path(tmp) / "sandboxes"
            run_root = prepare_run_root(new_default_run_root(base=sandbox_base), sandbox_base=sandbox_base)
            log_path = run_root / "transcripts" / "live-protocol" / "wrapper-log.jsonl"
            wrapper = create_workroot_command_wrapper(run_root=run_root, command_log_path=log_path)

            prepared_again = prepare_run_root(run_root, sandbox_base=sandbox_base)

            self.assertEqual(prepared_again, run_root)
            self.assertFalse(wrapper.exists())

    def test_command_classifier_reads_semantic_sequence(self) -> None:
        records = [
            {"argv": ["context", "--agent", "codex", "--cwd", "."]},
            {"argv": ["agent", "sync", "--reason", "before_work"]},
            {"argv": ["agent", "commit", "--request", "intent.json"]},
            {"argv": ["agent", "commit", "--request", "progress.json"]},
            {"argv": ["agent", "sync", "--reason", "continue"]},
        ]

        self.assertEqual(
            classify_workroot_commands(records),
            ["context", "agent sync", "agent commit", "agent commit", "agent sync"],
        )

    def test_discovery_classifier_distinguishes_sync_without_commit(self) -> None:
        self.assertEqual(classify_protocol_discovery(["context", "agent sync"], returncode=0), "discovered_sync")
        self.assertEqual(
            classify_protocol_discovery(["context", "agent sync", "agent commit"], returncode=0),
            "discovered_full_protocol",
        )
        self.assertEqual(classify_protocol_discovery(["context"], returncode=0), "context_only")

    def test_live_protocol_summary_merges_quarantined_case_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp) / "run-summary"
            original_db_summary = run_root / "transcripts" / "live-protocol" / "guided-minimal-loop" / "db-summary.json"
            quarantined_db_summary = (
                run_root
                / "reports"
                / "quarantine"
                / "20260527T000001Z"
                / "transcripts"
                / "live-protocol"
                / "guided-minimal-loop"
                / "db-summary.json"
            )
            current_summary = run_root / "reports" / "live-protocol-summary.json"
            quarantined_summary = (
                run_root / "reports" / "quarantine" / "20260527T000000Z" / "reports" / "live-protocol-summary.json"
            )
            quarantined_db_summary.parent.mkdir(parents=True, exist_ok=True)
            quarantined_db_summary.write_text("{}", encoding="utf-8")
            current_summary.parent.mkdir(parents=True, exist_ok=True)
            current_summary.write_text(
                json.dumps(
                    {
                        "returncode": 0,
                        "caseResults": [
                            {
                                "name": "guided-minimal-loop",
                                "returncode": 0,
                                "classification": "",
                                "stdout": "/tmp/guided-out",
                                "stderr": "/tmp/guided-err",
                                "lastMessage": "/tmp/guided-last",
                                "commandLog": "/tmp/guided-log",
                                "dbSummary": str(original_db_summary),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            quarantined_summary.parent.mkdir(parents=True, exist_ok=True)
            quarantined_summary.write_text(
                json.dumps(
                    {
                        "returncode": 0,
                        "caseResults": [
                            {
                                "name": "guided-minimal-loop",
                                "returncode": 0,
                                "classification": "",
                                "stdout": "/tmp/guided-out",
                                "stderr": "/tmp/guided-err",
                                "lastMessage": "/tmp/guided-last",
                                "commandLog": "/tmp/guided-log",
                                "dbSummary": str(original_db_summary),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            write_live_protocol_summary(
                run_root,
                case_results=(
                    {
                        "name": "discovery-diagnostic",
                        "returncode": 0,
                        "classification": "discovered_sync",
                        "stdout": "/tmp/discovery-out",
                        "stderr": "/tmp/discovery-err",
                        "lastMessage": "/tmp/discovery-last",
                        "commandLog": "/tmp/discovery-log",
                        "dbSummary": "/tmp/discovery-db",
                    },
                ),
            )

            summary = json.loads(current_summary.read_text(encoding="utf-8"))
            self.assertEqual(
                [item["name"] for item in summary["caseResults"]], ["guided-minimal-loop", "discovery-diagnostic"]
            )
            self.assertEqual(summary["caseResults"][0]["dbSummary"], str(quarantined_db_summary))
            self.assertEqual(summary["returncode"], 0)

    def test_codex_remote_option_is_global_when_configured(self) -> None:
        command = build_codex_command(
            codex="/opt/homebrew/bin/codex",
            user_directory=Path("/tmp/user"),
            ai_workroot_home=Path("/tmp/ai-home"),
            last_message_path=Path("/tmp/last.txt"),
            prompt="hello",
            remote="ws://127.0.0.1:4321",
        )

        self.assertEqual(command[:4], ("/opt/homebrew/bin/codex", "--remote", "ws://127.0.0.1:4321", "exec"))

    def test_database_summary_counts_protocol_facts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox_base = Path(tmp) / "sandboxes"
            run_root = prepare_run_root(new_default_run_root(base=sandbox_base), sandbox_base=sandbox_base)
            ai_home = run_root / "ai-workroot-home"
            env = env_for(ai_home)
            user_dir = run_root / "user-dirs" / "live-protocol"
            user_dir.mkdir(parents=True)
            init = run_cli(
                (
                    "init",
                    "--name",
                    "Live Protocol",
                    "--directory",
                    str(user_dir),
                    "--id",
                    WORKROOT_ID,
                    "--native-agent-entry",
                ),
                env=env,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            summary = summarize_workroot_database(ai_home=ai_home, workroot_id=WORKROOT_ID)

            self.assertEqual(summary["tasks"], 0)
            self.assertEqual(summary["taskRuns"], 0)
            self.assertEqual(summary["protocolEvents"], [])


class LiveProtocolE2ETest(unittest.TestCase):
    def test_codex_guided_protocol_minimal_loop(self) -> None:
        run_root, sandbox_base = self.require_live_runner()

        result = run_guided_minimal_loop(run_root=run_root, sandbox_base=sandbox_base)

        self.assertEqual(result.returncode, 0, result.failure_report())
        self.assertIn("LIVE_PROTOCOL_GUIDED_OK", result.last_message_path.read_text(encoding="utf-8"))
        records = self.read_command_log(result.command_log_path)
        commands = classify_workroot_commands(records)
        for expected in ("context", "agent sync", "agent commit", "agent commit", "agent commit", "agent sync"):
            self.assertIn(expected, commands)
        summary = json.loads(result.db_summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["tasks"], 1)
        self.assertEqual(summary["taskRuns"], 1)
        self.assertEqual(summary["taskSummariesCurrent"], 1)
        self.assertEqual(summary["handoffsCurrent"], 1)
        event_statuses = {(event["kind"], event["status"]) for event in summary["protocolEvents"]}
        self.assertIn(("intent", "applied"), event_statuses)
        self.assertIn(("progress", "applied"), event_statuses)
        self.assertIn(("handoff", "applied"), event_statuses)
        self.assertFalse(any(event["status"] in {"invalid", "quarantined"} for event in summary["protocolEvents"]))
        self.assertEqual(summary["userDirectoryRuntimeArtifacts"], [])

    def test_codex_continues_from_previous_handoff(self) -> None:
        run_root, sandbox_base = self.require_live_runner()
        first = run_guided_minimal_loop(run_root=run_root, sandbox_base=sandbox_base)
        self.assertEqual(first.returncode, 0, first.failure_report())

        result = run_continuation_from_handoff(run_root=run_root, sandbox_base=sandbox_base)

        self.assertEqual(result.returncode, 0, result.failure_report())
        final = result.last_message_path.read_text(encoding="utf-8")
        self.assertIn("LIVE_PROTOCOL_CONTINUE_OK", final)
        self.assertIn("Review the live protocol transcript", final)
        summary = json.loads(result.db_summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["tasks"], 1)

    def test_codex_degraded_commit_does_not_block_user_work(self) -> None:
        run_root, sandbox_base = self.require_live_runner()

        result = run_degraded_commit_case(run_root=run_root, sandbox_base=sandbox_base)

        self.assertEqual(result.returncode, 0, result.failure_report())
        self.assertIn("LIVE_PROTOCOL_DEGRADED_OK", result.last_message_path.read_text(encoding="utf-8"))
        summary = json.loads(result.db_summary_path.read_text(encoding="utf-8"))
        degraded_batch = next(
            batch for batch in summary["protocolBatches"] if batch["idempotencyKey"] == "idem-live-degraded-progress"
        )
        latest_batch = json.loads(degraded_batch["responseJson"])
        self.assertTrue(latest_batch["agent_may_continue"])
        self.assertEqual(latest_batch["result"]["status"], "applied")
        self.assertTrue(latest_batch["result"]["accepted"])
        self.assertIn("lease_expired_safe_projection", latest_batch["result"]["warnings"])
        self.assertEqual(summary["userDirectoryRuntimeArtifacts"], [])

    def test_codex_discovery_from_workroot_guidance(self) -> None:
        run_root, sandbox_base = self.require_live_runner()

        result = run_discovery_diagnostic(run_root=run_root, sandbox_base=sandbox_base)

        self.assertIn(
            result.classification,
            {"discovered_full_protocol", "discovered_sync", "context_only", "no_workroot_call", "failed"},
            result.failure_report(),
        )
        summary = json.loads(result.db_summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["classification"], result.classification)

    def require_live_runner(self) -> tuple[Path, Path]:
        require_e2e_runner_active(self, "live-protocol")
        run_root = os.environ.get("AI_WORKROOT_E2E_RUN_ROOT")
        sandbox_base = os.environ.get("AI_WORKROOT_E2E_SANDBOX_BASE")
        if not run_root or not sandbox_base:
            self.skipTest("live-protocol E2E must run through tests.e2e.runner")
        if os.environ.get("AI_WORKROOT_E2E_ALLOW_REMOTE_LLM") != "1":
            self.skipTest("remote LLM opt-in is required")
        return Path(run_root), Path(sandbox_base)

    def read_command_log(self, path: Path) -> list[dict[str, object]]:
        if not path.is_file():
            self.fail(f"missing Workroot command log: {path}")
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


if __name__ == "__main__":
    unittest.main()
