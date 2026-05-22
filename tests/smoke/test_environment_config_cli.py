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

            first = run_workroot_cli(env, "init", "--name", "First", "--directory", str(base / "first"), "--no-native-agent-entry")
            second = run_workroot_cli(env, "init", "--name", "Second", "--directory", str(base / "second"), "--no-native-agent-entry")

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

            result = run_workroot_cli(env, "init", "--name", "Summary", "--directory", str(base / "project"), "--no-native-agent-entry")

            self.assertEqual(result.returncode, 0, result.stderr)
            config = json.loads((home / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["kind"], "WorkrootEnvironment")
            self.assertEqual(config["environmentId"], "env_local_default")
            self.assertEqual(config["mode"], "clean")
            self.assertRegex(config["createdAt"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
            self.assertRegex(config["updatedAt"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
            self.assertEqual(config["summary"]["registeredWorkrootCount"], 1)
            self.assertEqual(config["summary"]["activeWorkrootCount"], 1)
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
