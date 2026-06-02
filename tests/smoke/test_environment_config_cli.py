from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.support.cli import run_workroot_cli


class EnvironmentConfigCliSmokeTest(unittest.TestCase):
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

            first = run_workroot_cli(
                env, "init", "--name", "First", "--directory", str(base / "first"), "--no-native-agent-entry"
            )
            second = run_workroot_cli(
                env, "init", "--name", "Second", "--directory", str(base / "second"), "--no-native-agent-entry"
            )

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            config = json.loads((home / "config.json").read_text(encoding="utf-8"))
            operator_preferences = json.loads(
                (home / "preferences/operator-preferences.json").read_text(encoding="utf-8")
            )
            policy_defaults = json.loads((home / "preferences/policy-defaults.json").read_text(encoding="utf-8"))
            self.assertEqual(config["custom"], "keep-me")
            self.assertEqual(config["kind"], "WorkrootEnvironment")
            self.assertEqual(config["version"], "0.9.531")
            self.assertEqual(config["summary"]["registeredWorkrootCount"], 2)
            self.assertEqual(config["summary"]["activeWorkrootCount"], 2)
            self.assertRegex(config["summary"]["lastRegistryUpdatedAt"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
            self.assertEqual(config["maintenance"]["status"], "idle")
            self.assertEqual(operator_preferences["customPreference"], "keep-me")
            self.assertEqual(operator_preferences["version"], "0.9.531")
            self.assertEqual(policy_defaults["customPolicy"], "keep-me")
            self.assertEqual(policy_defaults["version"], "0.9.531")

    def test_init_creates_minimal_environment_config_contract_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            env = {"AI_WORKROOT_HOME": str(home), "AI_WORKROOT_TIMEZONE": "Asia/Shanghai"}

            result = run_workroot_cli(
                env, "init", "--name", "Summary", "--directory", str(base / "project"), "--no-native-agent-entry"
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            config = json.loads((home / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["kind"], "WorkrootEnvironment")
            self.assertEqual(config["environmentId"], "env_local_default")
            self.assertEqual(config["mode"], "clean")
            self.assertEqual(config["time"]["timezone"], "Asia/Shanghai")
            self.assertEqual(config["time"]["locale"], "en-US")
            self.assertRegex(config["createdAt"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
            self.assertRegex(config["updatedAt"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
            self.assertEqual(config["summary"]["registeredWorkrootCount"], 1)
            self.assertEqual(config["summary"]["activeWorkrootCount"], 1)
            self.assertRegex(config["summary"]["lastRegistryUpdatedAt"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
            self.assertEqual(
                config["contextControl"],
                {
                    "defaultTargetTokens": 1200,
                    "defaultHardTokenLimit": 2400,
                    "diagnosticLogging": {
                        "enabled": False,
                        "includeRenderedPackage": False,
                        "includeTraceSummary": True,
                        "includeRetrievalSummary": True,
                        "includeTokenEstimate": True,
                        "retentionDays": 7,
                        "maxEntriesPerWorkroot": 200,
                    },
                },
            )
            self.assertNotIn("workroots", config)
            self.assertNotIn("policies", config)

    def test_environment_config_preserves_explicit_time_zone_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            home.mkdir()
            (home / "config.json").write_text(
                json.dumps(
                    {
                        "kind": "WorkrootEnvironment",
                        "time": {
                            "timezone": "America/Los_Angeles",
                            "locale": "zh-CN",
                        },
                    }
                ),
                encoding="utf-8",
            )

            result = run_workroot_cli(
                {"AI_WORKROOT_HOME": str(home), "AI_WORKROOT_TIMEZONE": "Asia/Shanghai"},
                "init",
                "--name",
                "Time",
                "--directory",
                str(base / "project"),
                "--no-native-agent-entry",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            config = json.loads((home / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["time"]["timezone"], "America/Los_Angeles")
            self.assertEqual(config["time"]["locale"], "zh-CN")
            self.assertRegex(config["createdAt"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_environment_config_does_not_reuse_legacy_visible_timestamps_on_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            home.mkdir()
            (home / "config.json").write_text(
                json.dumps(
                    {
                        "kind": "WorkrootEnvironment",
                        "createdAt": "2026-05-21T00:00:00Z",
                        "updatedAt": "2026-05-21T01:00:00Z",
                    }
                ),
                encoding="utf-8",
            )

            result = run_workroot_cli(
                {"AI_WORKROOT_HOME": str(home), "AI_WORKROOT_TIMEZONE": "Asia/Shanghai"},
                "init",
                "--name",
                "Migrated Time",
                "--directory",
                str(base / "project"),
                "--no-native-agent-entry",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            config = json.loads((home / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["createdAt"], "2026-05-21T00:00:00Z")
            self.assertRegex(config["updatedAt"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_environment_config_refreshes_update_time_on_registry_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            home.mkdir()
            (home / "config.json").write_text(
                json.dumps(
                    {
                        "kind": "WorkrootEnvironment",
                        "updatedAt": "2026-05-20T00:00:00Z",
                    }
                ),
                encoding="utf-8",
            )

            result = run_workroot_cli(
                {"AI_WORKROOT_HOME": str(home), "AI_WORKROOT_TIMEZONE": "Asia/Shanghai"},
                "init",
                "--name",
                "Refresh Time",
                "--directory",
                str(base / "project"),
                "--no-native-agent-entry",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            config = json.loads((home / "config.json").read_text(encoding="utf-8"))
            self.assertNotEqual(config["updatedAt"], "2026-05-20T00:00:00Z")
            self.assertEqual(config["updatedAt"], config["summary"]["lastRegistryUpdatedAt"])

    def test_environment_config_keeps_readable_top_level_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"

            result = run_workroot_cli(
                {"AI_WORKROOT_HOME": str(home), "AI_WORKROOT_TIMEZONE": "Asia/Shanghai"},
                "init",
                "--name",
                "Ordered Config",
                "--directory",
                str(base / "project"),
                "--no-native-agent-entry",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            config_text = (home / "config.json").read_text(encoding="utf-8")
            ordered_keys = [
                '"kind"',
                '"environmentId"',
                '"version"',
                '"schemaVersion"',
                '"layoutVersion"',
                '"mode"',
                '"createdAt"',
                '"updatedAt"',
                '"time"',
                '"maintenance"',
                '"summary"',
                '"contextControl"',
            ]
            positions = [config_text.index(key) for key in ordered_keys]
            self.assertEqual(positions, sorted(positions))

    def test_init_preserves_existing_context_control_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            home.mkdir()
            (home / "config.json").write_text(
                json.dumps(
                    {
                        "kind": "WorkrootEnvironment",
                        "contextControl": {
                            "defaultTargetTokens": 100,
                            "defaultHardTokenLimit": 200,
                            "diagnosticLogging": {
                                "enabled": True,
                                "includeRenderedPackage": True,
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            result = run_workroot_cli(
                {"AI_WORKROOT_HOME": str(home)},
                "init",
                "--name",
                "Config",
                "--directory",
                str(base / "project"),
                "--no-native-agent-entry",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            context_control = json.loads((home / "config.json").read_text(encoding="utf-8"))["contextControl"]
            self.assertEqual(context_control["defaultTargetTokens"], 100)
            self.assertEqual(context_control["defaultHardTokenLimit"], 200)
            self.assertTrue(context_control["diagnosticLogging"]["enabled"])
            self.assertTrue(context_control["diagnosticLogging"]["includeRenderedPackage"])
            self.assertTrue(context_control["diagnosticLogging"]["includeTraceSummary"])
            self.assertTrue(context_control["diagnosticLogging"]["includeRetrievalSummary"])


if __name__ == "__main__":
    unittest.main()
