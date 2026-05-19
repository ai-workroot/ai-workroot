from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/workroot_cli.py"


def run_cli(*args: str) -> str:
    result = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout


class WorkrootCliDiscoveryTest(unittest.TestCase):
    def test_quickstart_mentions_happy_path(self) -> None:
        out = run_cli("quickstart")
        self.assertIn("Clean Mode", out)
        self.assertIn("CLI wrapper installer", out)
        self.assertIn("legacy public-seed", out)
        self.assertIn("task complete", out)
        self.assertIn("manifest --format json", out)
        self.assertIn("recipe batch-12-tasks --format json", out)
        self.assertIn("continue rebuild", out)
        self.assertIn("schema", out)

    def test_cli_help_separates_clean_mode_from_legacy_seed_commands(self) -> None:
        out = run_cli("quickstart")

        self.assertIn("Clean Mode user path:", out)
        self.assertIn("workroot init", out)
        self.assertIn("workroot context", out)
        self.assertIn("workroot doctor", out)
        self.assertIn("legacy public-seed agent-operation commands:", out)

    def test_operation_manifest_marks_legacy_seed_commands(self) -> None:
        manifest = json.loads(run_cli("manifest", "--format", "json"))

        self.assertIn("legacy_mode", manifest)
        self.assertIn("legacy public-seed", manifest["legacy_mode"]["description"])
        self.assertIn("task", manifest["legacy_mode"]["commands"])
        self.assertIn("init, context, doctor, status, list", manifest["legacy_mode"]["description"])

    def test_manifest_json_exposes_agent_operation_contract(self) -> None:
        manifest = json.loads(run_cli("manifest", "--format", "json"))
        self.assertEqual(manifest["manifest_id"], "agent-operation-manifest")
        self.assertIn("scripts/workroot_client.py", manifest["normal_mode"]["do_not_read"])
        self.assertIn("task.create", manifest["batch_operations"])
        self.assertIn("run.add", manifest["batch_operations"])
        self.assertIn("mind.add", manifest["batch_operations"])
        self.assertIn("session.summarize", manifest["batch_operations"])
        self.assertIn("legacy public-seed", manifest["legacy_mode"]["description"])
        self.assertNotIn("mind.add", manifest["unsupported_batch_operations"])
        self.assertNotIn("run.add", manifest["unsupported_batch_operations"])
        self.assertTrue(manifest["batch_operations"]["artifact.add"]["fields"]["content"]["optional"])
        self.assertEqual(manifest["batch_operations"]["task.create"]["fields"]["process_level"]["default"], "L0")

    def test_schema_lists_enums_and_path_rules(self) -> None:
        out = run_cli("schema")
        self.assertIn("manual_check", out)
        self.assertIn("model_generation", out)
        self.assertIn("artifact audiences", out)
        self.assertIn("source_paths", out)
        self.assertIn("input_ref", out)

    def test_schema_json_lists_batch_operation_fields(self) -> None:
        schema = json.loads(run_cli("schema", "--format", "json"))
        self.assertIn("batch_operations", schema)
        self.assertIn("artifact.add", schema["batch_operations"])
        self.assertIn("compute_metadata", schema["batch_operations"]["artifact.add"]["fields"])
        self.assertIn("conclusion_preview", schema["batch_operations"]["run.add"]["fields"])
        self.assertIn("from_task_ids", schema["batch_operations"]["mind.add"]["fields"])
        self.assertIn("task_ids", schema["batch_operations"]["session.summarize"]["fields"])
        self.assertIn(
            "array of paths",
            schema["batch_operations"]["checkpoint.add"]["fields"]["required_context_paths"]["description"],
        )
        self.assertIn(
            "semicolon-separated",
            schema["batch_operations"]["retrieval_card.add"]["fields"]["source_paths"]["description"],
        )

    def test_recipe_batch_12_tasks_json_is_directly_usable(self) -> None:
        recipe = json.loads(run_cli("recipe", "batch-12-tasks", "--format", "json"))
        operations = recipe["operations"]
        self.assertEqual(len([op for op in operations if op["op"] == "task.create"]), 12)
        self.assertEqual(len([op for op in operations if op["op"] == "artifact.add"]), 12)
        self.assertEqual(operations[-1]["op"], "session.summarize")

    def test_recipe_task_l2_evidence(self) -> None:
        out = run_cli("recipe", "task-l2-evidence")
        self.assertIn("task complete", out)
        self.assertIn("--process-level L2", out)
        self.assertIn("--checkpoint", out)
        self.assertIn("--report-content-file", out)

    def test_doctor_runs_kernel_validation(self) -> None:
        out = run_cli("doctor")
        self.assertIn("AI Workroot kernel validation passed.", out)


if __name__ == "__main__":
    unittest.main()
