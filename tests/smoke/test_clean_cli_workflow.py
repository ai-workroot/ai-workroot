from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tests.support.cli import run_workroot_cli


class CleanCliWorkflowSmokeTest(unittest.TestCase):
    def test_init_list_status_context_and_doctor_use_clean_managed_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            (user_dir / "note.md").write_text("Clean Workroot note\n", encoding="utf-8")
            env = {"AI_WORKROOT_HOME": str(home)}

            init = run_workroot_cli(
                env, "init", "--name", "Demo Workroot", "--directory", str(user_dir), "--no-native-agent-entry"
            )

            self.assertEqual(init.returncode, 0, init.stderr)
            self.assertIn("initialized", init.stdout)
            self.assertEqual(sorted(path.name for path in user_dir.iterdir()), ["note.md", "workroot-output"])
            self.assertTrue((user_dir / "workroot-output" / "START_HERE.txt").is_file())
            self.assertTrue((home / "registry/workroots.jsonl").is_file())
            self.assertFalse((user_dir / ".workroot").exists())
            self.assertFalse((user_dir / ".ai-workroot").exists())
            self.assertFalse((user_dir / "context").exists())
            self.assertFalse((user_dir / "logs").exists())

            listed = run_workroot_cli(env, "list", "--format", "json")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            records = json.loads(listed.stdout)
            self.assertEqual(len(records), 1)
            workroot_id = records[0]["workrootId"]
            self.assertRegex(workroot_id, r"^wr_demo_workroot_[a-z0-9]{8}$")
            self.assertTrue((home / f"workroots/{workroot_id}/cache/workroot.sqlite").is_file())

            status = run_workroot_cli(env, "status", "--cwd", str(user_dir))
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn("Demo Workroot", status.stdout)
            self.assertIn(workroot_id, status.stdout)

            context = run_workroot_cli(
                env, "context", "--agent", "codex", "--cwd", str(user_dir), "--query", "Clean Mode"
            )
            self.assertEqual(context.returncode, 0, context.stderr)
            self.assertIn("# AI Workroot Context Package", context.stdout)
            self.assertIn("Mode: standard", context.stdout)
            self.assertIn("Confidence:", context.stdout)
            self.assertIn("LatencyMs:", context.stdout)
            self.assertIn("TokenUsage:", context.stdout)
            self.assertIn("Query: Clean Mode", context.stdout)

            debug = run_workroot_cli(env, "context", "--agent", "codex", "--cwd", str(user_dir), "--debug")
            self.assertEqual(debug.returncode, 0, debug.stderr)
            self.assertIn("Debug Trace", debug.stdout)
            self.assertIn("candidateSources", debug.stdout)
            self.assertIn("timing", debug.stdout)
            self.assertIn("tokenUsage", debug.stdout)

            agent_sync = run_workroot_cli(
                env,
                "agent",
                "sync",
                "--agent",
                "codex",
                "--cwd",
                str(user_dir),
                "--reason",
                "before_work",
                "--query",
                "Clean Mode",
                "--work-signal",
                '{"phase":"starting","work_kind":"task","intended_action":"plan","focus":"Clean Mode"}',
            )
            self.assertEqual(agent_sync.returncode, 0, agent_sync.stderr)
            sync_response = json.loads(agent_sync.stdout)
            self.assertTrue(sync_response["agent_may_continue"])
            self.assertEqual(sync_response["workroot_contract"]["next_exchange"]["action"], "commit")
            self.assertIn("Workroot Guidance", sync_response["workroot_guidance"])
            self.assertEqual(sync_response["workroot_view"]["output_rules"][0]["path"], "workroot-output")

            packet_sync = run_workroot_cli(
                env,
                "agent",
                "sync",
                "--agent",
                "codex",
                "--cwd",
                str(user_dir),
                "--reason",
                "before_work",
                "--query",
                "Clean Mode",
                "--format",
                "packet",
                "--work-signal",
                '{"phase":"starting","work_kind":"task","intended_action":"plan","focus":"Clean Mode"}',
            )
            self.assertEqual(packet_sync.returncode, 0, packet_sync.stderr)
            self.assertIn('"output": {', packet_sync.stdout)
            self.assertIn('"default_path": "workroot-output"', packet_sync.stdout)
            self.assertIn('"asset_path_required": true', packet_sync.stdout)

            rule_sync = run_workroot_cli(
                env,
                "agent",
                "sync",
                "--agent",
                "codex",
                "--cwd",
                str(user_dir),
                "--reason",
                "before_work",
                "--query",
                "Remember that future reports should go in reports.",
                "--work-signal",
                '{"phase":"planning","work_kind":"operations","intended_action":"preserve","refs":["output_rule:report"]}',
            )
            self.assertEqual(rule_sync.returncode, 0, rule_sync.stderr)
            rule_sync_response = json.loads(rule_sync.stdout)
            rule_commit = run_workroot_cli(
                env,
                "agent",
                "commit",
                "--shape",
                "state-update",
                "--lease",
                rule_sync_response["workroot_contract"]["commit_contract"]["lease_id"],
                "--cwd",
                str(user_dir),
                "--target",
                "output-rule:report",
                "--change",
                "path reports",
            )
            self.assertEqual(rule_commit.returncode, 0, rule_commit.stderr)
            rule_commit_response = json.loads(rule_commit.stdout)
            self.assertTrue(rule_commit_response["ok"])
            self.assertIn(
                {"asset_kind": "report", "path": "reports", "role": "declared_output"},
                rule_commit_response["workroot_view"]["output_rules"],
            )

            agent_sync_after_rule = run_workroot_cli(
                env,
                "agent",
                "sync",
                "--agent",
                "codex",
                "--cwd",
                str(user_dir),
                "--reason",
                "before_work",
                "--query",
                "Clean Mode",
                "--work-signal",
                '{"phase":"starting","work_kind":"task","intended_action":"plan","focus":"Clean Mode"}',
            )
            self.assertEqual(agent_sync_after_rule.returncode, 0, agent_sync_after_rule.stderr)
            sync_after_rule_response = json.loads(agent_sync_after_rule.stdout)
            self.assertIn(
                {"asset_kind": "report", "path": "reports", "role": "declared_output"},
                sync_after_rule_response["workroot_view"]["output_rules"],
            )

            intent = run_workroot_cli(
                env,
                "agent",
                "commit",
                "--shape",
                "start-work",
                "--lease",
                sync_after_rule_response["workroot_contract"]["commit_contract"]["lease_id"],
                "--cwd",
                str(user_dir),
                "--title",
                "Clean Mode CLI shorthand",
                "--summary",
                "Track Clean Mode through shorthand commit.",
            )
            self.assertEqual(intent.returncode, 0, intent.stderr)
            intent_response = json.loads(intent.stdout)
            self.assertTrue(intent_response["ok"])
            self.assertEqual(intent_response["result"]["status"], "applied")
            self.assertTrue(intent_response["workroot_contract"]["state_refs"]["task_ref"].startswith("task-evt-auto-"))
            self.assertTrue(intent_response["workroot_contract"]["state_refs"]["run_ref"].startswith("run-evt-auto-"))

            progress = run_workroot_cli(
                env,
                "agent",
                "commit",
                "--shape",
                "checkpoint",
                "--lease",
                intent_response["workroot_contract"]["commit_contract"]["lease_id"],
                "--cwd",
                str(user_dir),
                "--summary",
                "Shorthand progress was projected.",
                "--done",
                "Commit intent through shorthand",
            )
            self.assertEqual(progress.returncode, 0, progress.stderr)
            progress_response = json.loads(progress.stdout)
            self.assertTrue(progress_response["ok"])
            sqlite_path = home / f"workroots/{workroot_id}/cache/workroot.sqlite"
            with sqlite3.connect(sqlite_path) as conn:
                effect_types = {
                    row[0] for row in conn.execute("SELECT effect_type FROM protocol_event_effects").fetchall()
                }
            self.assertIn("task_summary_created", effect_types)
            self.assertIn("task_item_created", effect_types)

            handoff = run_workroot_cli(
                env,
                "agent",
                "commit",
                "--shape",
                "continuation",
                "--lease",
                progress_response["workroot_contract"]["commit_contract"]["lease_id"],
                "--cwd",
                str(user_dir),
                "--state",
                "Shorthand loop is preserved.",
                "--next",
                "Review shorthand command output.",
            )
            self.assertEqual(handoff.returncode, 0, handoff.stderr)
            handoff_response = json.loads(handoff.stdout)
            self.assertTrue(handoff_response["ok"])
            self.assertEqual(handoff_response["workroot_contract"]["next_exchange"]["action"], "none")

            doctor = run_workroot_cli(env, "doctor", "--cwd", str(user_dir))
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            self.assertIn("AI Workroot doctor: PASS", doctor.stdout)

    def test_init_requires_native_entry_authorization_before_user_directory_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            env = {"AI_WORKROOT_HOME": str(home)}

            without_entry = run_workroot_cli(
                env,
                "init",
                "--name",
                "No Entry",
                "--directory",
                str(user_dir),
                "--no-native-agent-entry",
            )
            self.assertEqual(without_entry.returncode, 0, without_entry.stderr)
            self.assertFalse((user_dir / "AGENTS.md").exists())
            self.assertFalse((user_dir / "CLAUDE.md").exists())

            second_user_dir = base / "project-entry"
            with_entry = run_workroot_cli(
                env,
                "init",
                "--name",
                "With Entry",
                "--directory",
                str(second_user_dir),
                "--native-agent-entry",
            )
            self.assertEqual(with_entry.returncode, 0, with_entry.stderr)
            self.assertIn(
                'workroot agent sync --agent codex --cwd . --query "<current user request>" --format packet',
                (second_user_dir / "AGENTS.md").read_text(encoding="utf-8"),
            )
            self.assertIn(
                'workroot agent sync --agent claude --cwd . --query "<current user request>" --format packet',
                (second_user_dir / "CLAUDE.md").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
