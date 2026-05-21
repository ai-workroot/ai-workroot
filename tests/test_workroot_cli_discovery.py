from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from ai_workroot.cli import legacy_seed
from ai_workroot.runtime.legacy_seed import operation_manifest


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/compat/workroot_cli.py"


def run_cli(*args: str) -> str:
    result = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout


def run_cli_without_pythonpath(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def run_package_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "ai_workroot", *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


class WorkrootCliDiscoveryTest(unittest.TestCase):
    def test_package_legacy_cli_exports_parser_and_main(self) -> None:
        parser = legacy_seed.build_parser()

        self.assertTrue(callable(legacy_seed.main))
        self.assertIn("quickstart", parser.format_help())

    def test_operation_manifest_is_loaded_from_legacy_seed_runtime(self) -> None:
        manifest = operation_manifest.manifest()

        self.assertIn("legacy_mode", manifest)
        self.assertIn("task", manifest["legacy_mode"]["commands"])

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

    def test_default_help_hides_legacy_seed_commands(self) -> None:
        out = run_cli("--help")

        self.assertIn("init", out)
        self.assertIn("context", out)
        self.assertIn("doctor", out)
        for legacy in ("task", "run", "action", "artifact", "retrieval-card", "checkpoint", "invalidation", "mind", "session", "continue", "batch"):
            self.assertNotIn(legacy, out)

    def test_package_default_help_hides_legacy_namespace(self) -> None:
        out = run_package_cli("--help")

        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("init", out.stdout)
        self.assertIn("context", out.stdout)
        self.assertIn("doctor", out.stdout)
        self.assertNotIn("legacy", out.stdout)
        self.assertNotIn("==SUPPRESS==", out.stdout)

    def test_compat_clean_commands_work_without_pythonpath(self) -> None:
        init_help = run_cli_without_pythonpath("init", "--help")
        release_doctor = run_cli_without_pythonpath("doctor", "--release")

        self.assertEqual(init_help.returncode, 0, init_help.stderr)
        self.assertIn("usage: workroot init", init_help.stdout)
        self.assertIn("--directory", init_help.stdout)
        self.assertEqual(release_doctor.returncode, 0, release_doctor.stderr)
        self.assertIn("AI Workroot release doctor: PASS", release_doctor.stdout)

    def test_package_cli_exposes_hidden_legacy_command_surface(self) -> None:
        manifest = run_package_cli("legacy", "manifest", "--format", "json")
        recipe = run_package_cli("legacy", "recipe", "task-l2-evidence")

        self.assertEqual(manifest.returncode, 0, manifest.stderr)
        self.assertEqual(recipe.returncode, 0, recipe.stderr)
        data = json.loads(manifest.stdout)
        self.assertEqual(data["manifest_id"], "agent-operation-manifest")
        self.assertIn("workroot legacy batch apply --file plan.json", data["batch"]["command"])
        self.assertIn("workroot legacy task create", recipe.stdout)
        self.assertNotIn("scripts/compat/workroot_cli.py", manifest.stdout)
        self.assertNotIn("scripts/compat/workroot_cli.py", recipe.stdout)

    def test_package_legacy_help_delegates_to_legacy_parser(self) -> None:
        help_result = run_package_cli("legacy", "--help")

        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("quickstart", help_result.stdout)
        self.assertIn("manifest", help_result.stdout)
        self.assertIn("recipe", help_result.stdout)
        self.assertIn("legacy public-seed", help_result.stdout)
        self.assertNotIn("legacy_args", help_result.stdout)

    def test_operation_manifest_marks_legacy_seed_commands(self) -> None:
        manifest = json.loads(run_cli("manifest", "--format", "json"))

        self.assertIn("legacy_mode", manifest)
        self.assertIn("legacy public-seed", manifest["legacy_mode"]["description"])
        self.assertIn("task", manifest["legacy_mode"]["commands"])
        self.assertIn("init, context, doctor, status, list", manifest["legacy_mode"]["description"])

    def test_manifest_json_exposes_agent_operation_contract(self) -> None:
        manifest = json.loads(run_cli("manifest", "--format", "json"))
        self.assertEqual(manifest["manifest_id"], "agent-operation-manifest")
        self.assertIn("implementation source modules", manifest["normal_mode"]["do_not_read"])
        self.assertIn("historical execution plans", manifest["normal_mode"]["do_not_read"])
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
