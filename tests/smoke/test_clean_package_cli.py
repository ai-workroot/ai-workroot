from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class CleanPackageCliSmokeTest(unittest.TestCase):
    def run_cli(self, env: dict[str, str], *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "ai_workroot", *args],
            cwd=cwd or ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT / "src"), **env},
            text=True,
            capture_output=True,
            check=False,
        )

    def test_init_list_status_context_and_doctor_use_clean_managed_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            (user_dir / "note.md").write_text("Clean Workroot note\n", encoding="utf-8")
            env = {"AI_WORKROOT_HOME": str(home)}

            init = self.run_cli(env, "init", "--name", "Demo Workroot", "--directory", str(user_dir), "--no-native-agent-entry")

            self.assertEqual(init.returncode, 0, init.stderr)
            self.assertIn("initialized", init.stdout)
            self.assertEqual(sorted(path.name for path in user_dir.iterdir()), ["note.md"])
            self.assertTrue((home / "registry/workroots.jsonl").is_file())
            self.assertFalse((user_dir / ".workroot").exists())
            self.assertFalse((user_dir / ".ai-workroot").exists())
            self.assertFalse((user_dir / "context").exists())
            self.assertFalse((user_dir / "logs").exists())

            listed = self.run_cli(env, "list", "--format", "json")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            records = json.loads(listed.stdout)
            self.assertEqual(len(records), 1)
            workroot_id = records[0]["workrootId"]
            self.assertRegex(workroot_id, r"^wr_demo_workroot_[a-z0-9]{8}$")
            self.assertTrue((home / f"workroots/{workroot_id}/cache/workroot.sqlite").is_file())

            status = self.run_cli(env, "status", "--cwd", str(user_dir))
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn("Demo Workroot", status.stdout)
            self.assertIn(workroot_id, status.stdout)

            context = self.run_cli(env, "context", "--agent", "codex", "--cwd", str(user_dir), "--query", "Clean Mode")
            self.assertEqual(context.returncode, 0, context.stderr)
            self.assertIn("# AI Workroot Context Package", context.stdout)
            self.assertIn("Mode: standard", context.stdout)
            self.assertIn("Confidence:", context.stdout)
            self.assertIn("LatencyMs:", context.stdout)
            self.assertIn("TokenUsage:", context.stdout)
            self.assertIn("Query: Clean Mode", context.stdout)

            debug = self.run_cli(env, "context", "--agent", "codex", "--cwd", str(user_dir), "--debug")
            self.assertEqual(debug.returncode, 0, debug.stderr)
            self.assertIn("Debug Trace", debug.stdout)
            self.assertIn("candidateSources", debug.stdout)
            self.assertIn("timing", debug.stdout)
            self.assertIn("tokenUsage", debug.stdout)

            doctor = self.run_cli(env, "doctor", "--cwd", str(user_dir))
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            self.assertIn("AI Workroot doctor: PASS", doctor.stdout)

    def test_init_preserves_existing_environment_config_and_preferences(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            home.mkdir()
            (home / "preferences").mkdir()
            (home / "config.json").write_text(
                json.dumps({"version": "custom", "kind": "WorkrootEnvironment", "custom": "keep-me"}),
                encoding="utf-8",
            )
            (home / "preferences/operator-preferences.json").write_text(
                json.dumps({"customPreference": "keep-me"}),
                encoding="utf-8",
            )
            (home / "preferences/policy-defaults.json").write_text(
                json.dumps({"customPolicy": "keep-me"}),
                encoding="utf-8",
            )
            env = {"AI_WORKROOT_HOME": str(home)}

            first = self.run_cli(env, "init", "--name", "First", "--directory", str(base / "first"), "--no-native-agent-entry")
            second = self.run_cli(env, "init", "--name", "Second", "--directory", str(base / "second"), "--no-native-agent-entry")

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            config = json.loads((home / "config.json").read_text(encoding="utf-8"))
            operator_preferences = json.loads((home / "preferences/operator-preferences.json").read_text(encoding="utf-8"))
            policy_defaults = json.loads((home / "preferences/policy-defaults.json").read_text(encoding="utf-8"))
            self.assertEqual(config["custom"], "keep-me")
            self.assertEqual(config["kind"], "WorkrootEnvironment")
            self.assertEqual(config["version"], "0.9.530")
            self.assertEqual(config["summary"]["registeredWorkrootCount"], 2)
            self.assertEqual(config["summary"]["activeWorkrootCount"], 2)
            self.assertRegex(config["summary"]["lastRegistryUpdatedAt"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
            self.assertEqual(config["maintenance"]["status"], "idle")
            self.assertEqual(operator_preferences["customPreference"], "keep-me")
            self.assertEqual(operator_preferences["version"], "0.9.530")
            self.assertEqual(policy_defaults["customPolicy"], "keep-me")
            self.assertEqual(policy_defaults["version"], "0.9.530")

    def test_init_creates_minimal_environment_config_contract_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            env = {"AI_WORKROOT_HOME": str(home)}

            result = self.run_cli(env, "init", "--name", "Summary", "--directory", str(base / "project"), "--no-native-agent-entry")

            self.assertEqual(result.returncode, 0, result.stderr)
            config = json.loads((home / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["kind"], "WorkrootEnvironment")
            self.assertEqual(config["environmentId"], "env_local_default")
            self.assertEqual(config["mode"], "clean")
            self.assertRegex(config["createdAt"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
            self.assertRegex(config["updatedAt"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
            self.assertEqual(config["summary"]["registeredWorkrootCount"], 1)
            self.assertEqual(config["summary"]["activeWorkrootCount"], 1)
            self.assertNotIn("workroots", config)
            self.assertNotIn("policies", config)

    def test_doctor_records_environment_summary_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            env = {"AI_WORKROOT_HOME": str(home)}
            init = self.run_cli(env, "init", "--name", "Doctor Summary", "--directory", str(user_dir), "--no-native-agent-entry")
            self.assertEqual(init.returncode, 0, init.stderr)

            doctor = self.run_cli(env, "doctor", "--cwd", str(user_dir))

            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            config = json.loads((home / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["summary"]["lastDoctorStatus"], "PASS")
            self.assertRegex(config["summary"]["lastDoctorRunAt"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_doctor_records_summary_in_explicit_environment_home_not_registry_state_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            fake_home = base / "fake-home"
            user_dir = base / "project"
            env = {"AI_WORKROOT_HOME": str(home)}
            init = self.run_cli(env, "init", "--name", "Doctor Home", "--directory", str(user_dir), "--no-native-agent-entry")
            self.assertEqual(init.returncode, 0, init.stderr)
            record_path = home / "registry/workroots.jsonl"
            record = json.loads(record_path.read_text(encoding="utf-8").splitlines()[0])
            fake_state = fake_home / "workroots" / record["workroot_id"]
            fake_state.mkdir(parents=True)
            original_state = Path(record["state_directory"])
            (fake_state / "workroot.json").write_text(
                (original_state / "workroot.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            record["state_directory"] = str(fake_state)
            record_path.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

            doctor = self.run_cli(env, "doctor", "--cwd", str(user_dir))

            self.assertNotEqual(doctor.returncode, 0)
            real_config = json.loads((home / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(real_config["summary"]["lastDoctorStatus"], "FAIL")
            self.assertFalse((fake_home / "config.json").exists())

    def test_doctor_reports_missing_sqlite_table_without_repairing_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            env = {"AI_WORKROOT_HOME": str(home)}
            init = self.run_cli(env, "init", "--name", "Demo", "--directory", str(user_dir), "--no-native-agent-entry")
            self.assertEqual(init.returncode, 0, init.stderr)
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                conn.execute("DROP TABLE context_candidates")

            doctor = self.run_cli(env, "doctor", "--cwd", str(user_dir))

            self.assertNotEqual(doctor.returncode, 0)
            self.assertIn("missing SQLite table: context_candidates", doctor.stdout)
            with sqlite3.connect(db_path) as conn:
                table = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'context_candidates'"
                ).fetchone()
            self.assertIsNone(table)

    def test_init_requires_native_entry_authorization_before_user_directory_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            env = {"AI_WORKROOT_HOME": str(home)}

            without_entry = self.run_cli(
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
            with_entry = self.run_cli(
                env,
                "init",
                "--name",
                "With Entry",
                "--directory",
                str(second_user_dir),
                "--native-agent-entry",
            )
            self.assertEqual(with_entry.returncode, 0, with_entry.stderr)
            self.assertIn("workroot context --agent codex --cwd .", (second_user_dir / "AGENTS.md").read_text(encoding="utf-8"))
            self.assertIn("workroot context --agent claude --cwd .", (second_user_dir / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_context_help_exposes_hard_token_limit(self) -> None:
        result = self.run_cli({}, "context", "--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--hard-token-limit", result.stdout)
        self.assertIn("--target-tokens", result.stdout)

    def test_context_hard_token_limit_has_final_estimator_fallback(self) -> None:
        from ai_workroot.runtime.context import _enforce_hard_token_limit, estimate_tokens

        rendered = "# AI Workroot Context Package\n" + ("这是没有空格的中文内容" * 100)

        trimmed, steps = _enforce_hard_token_limit(rendered, 1)

        self.assertIn("final-fallback", steps)
        self.assertLessEqual(estimate_tokens(trimmed), 1)
        self.assertNotEqual(trimmed.strip(), "")

    def test_unix_install_wrapper_installs_new_package_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            install_dir = Path(tmp) / "bin"
            env = {**os.environ, "AI_WORKROOT_INSTALL_DIR": str(install_dir)}

            dry_run = subprocess.run(
                [str(ROOT / "install/unix/install.sh"), "--dry-run"],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            install = subprocess.run(
                [str(ROOT / "install/unix/install.sh")],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
            self.assertIn("Clean Workroot package entrypoint", dry_run.stdout)
            self.assertEqual(install.returncode, 0, install.stderr)
            wrapper = install_dir / "workroot"
            self.assertTrue(wrapper.is_file())
            text = wrapper.read_text(encoding="utf-8")
            self.assertIn("python3 -m ai_workroot", text)
            self.assertNotIn("scripts/compat/workroot_cli.py", text)


if __name__ == "__main__":
    unittest.main()
