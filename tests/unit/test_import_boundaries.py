from __future__ import annotations

import ast
import sys
import unittest
from collections.abc import Iterable
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"


class ImportBoundariesTest(unittest.TestCase):
    def test_required_package_directories_exist(self) -> None:
        required = [
            "core",
            "contracts",
            "runtime",
            "storage",
            "indexing",
            "agent",
            "cli",
            "resources",
        ]

        for name in required:
            with self.subTest(name=name):
                self.assertTrue((SRC / "ai_workroot" / name / "__init__.py").is_file())

    def test_tests_root_contains_no_loose_test_modules(self) -> None:
        loose_tests = sorted(
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "tests").glob("test_*.py")
        )

        self.assertEqual(loose_tests, [])

    def test_required_test_directories_exist(self) -> None:
        required = [
            "contracts",
            "e2e",
            "fixtures",
            "integration",
            "negative",
            "smoke",
            "support",
            "unit",
        ]

        for name in required:
            with self.subTest(name=name):
                self.assertTrue((ROOT / "tests" / name).is_dir())

    def test_src_has_no_active_legacy_modules(self) -> None:
        legacy_paths = [
            path.relative_to(ROOT).as_posix()
            for path in (SRC / "ai_workroot").rglob("*")
            if "legacy" in path.relative_to(SRC).as_posix()
        ]

        self.assertEqual(legacy_paths, [])

    def test_src_does_not_import_legacy_modules(self) -> None:
        violations: list[str] = []
        forbidden = ("legacy_", ".legacy_", "legacy_seed", "public_seed")
        for path in (SRC / "ai_workroot").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                module_names: list[str] = []
                if isinstance(node, ast.Import):
                    module_names.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    module_names.append(node.module)
                for module in module_names:
                    if any(term in module for term in forbidden):
                        violations.append(f"{path.relative_to(ROOT)}:{getattr(node, 'lineno', 0)}:{module}")

        self.assertEqual(violations, [])

    def test_contracts_do_not_import_project_modules(self) -> None:
        contracts_dir = SRC / "ai_workroot" / "contracts"
        forbidden_prefix = "ai_workroot."

        for path in contracts_dir.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertFalse(
                            alias.name.startswith(forbidden_prefix),
                            f"{path.relative_to(ROOT)} imports {alias.name}",
                        )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    self.assertFalse(
                        node.module.startswith(forbidden_prefix),
                        f"{path.relative_to(ROOT)} imports from {node.module}",
                    )

    def test_core_does_not_import_infrastructure_layers(self) -> None:
        core_dir = SRC / "ai_workroot" / "core"
        forbidden = (
            "ai_workroot.storage",
            "ai_workroot.indexing",
            "ai_workroot.agent",
            "ai_workroot.cli",
        )

        for path in core_dir.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertFalse(
                            alias.name.startswith(forbidden),
                            f"{path.relative_to(ROOT)} imports {alias.name}",
                        )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    self.assertFalse(
                        node.module.startswith(forbidden),
                        f"{path.relative_to(ROOT)} imports from {node.module}",
                    )

    def test_cli_does_not_import_storage_or_indexing_directly(self) -> None:
        cli_dir = SRC / "ai_workroot" / "cli"
        forbidden = ("ai_workroot.storage", "ai_workroot.indexing")

        for path in cli_dir.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertFalse(
                            alias.name.startswith(forbidden),
                            f"{path.relative_to(ROOT)} imports {alias.name}",
                        )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    self.assertFalse(
                        node.module.startswith(forbidden),
                        f"{path.relative_to(ROOT)} imports from {node.module}",
                    )

    def test_src_does_not_import_scripts_package(self) -> None:
        for path in (SRC / "ai_workroot").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertFalse(
                            alias.name == "scripts" or alias.name.startswith("scripts."),
                            f"{path.relative_to(ROOT)} imports {alias.name}",
                        )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    self.assertFalse(
                        node.module == "scripts" or node.module.startswith("scripts."),
                        f"{path.relative_to(ROOT)} imports from {node.module}",
                    )

    def test_src_does_not_execute_scripts_paths(self) -> None:
        violations: list[str] = []
        for path in (SRC / "ai_workroot").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if _is_subprocess_run(node) and _call_contains_scripts_path(node):
                    violations.append(f"{path.relative_to(ROOT)}:{node.lineno}")

        self.assertEqual(violations, [])

    def test_src_does_not_publish_scripts_as_canonical_command_guidance(self) -> None:
        violations: list[str] = []
        for path in (SRC / "ai_workroot").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                for value in _string_constants(node):
                    if "scripts/" in value or "scripts\\" in value:
                        violations.append(f"{path.relative_to(ROOT)}:{getattr(node, 'lineno', 0)}:{value}")

        self.assertEqual(violations, [])

    def test_environment_config_uses_simple_canonical_time_field_names(self) -> None:
        environment_path = SRC / "ai_workroot" / "runtime" / "environment.py"
        tree = ast.parse(environment_path.read_text(encoding="utf-8"), filename=str(environment_path))
        forbidden = {
            "createdAtUtc",
            "updatedAtUtc",
            "lastRegistryUpdatedAtUtc",
            "lastDoctorRunAtUtc",
            "lastMigrationAtUtc",
            "startedAtUtc",
            "completedAtUtc",
            "createdAtLocal",
            "updatedAtLocal",
        }
        violations: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for key in node.keys:
                    if isinstance(key, ast.Constant) and key.value in forbidden:
                        violations.append(f"{environment_path.relative_to(ROOT)}:{key.lineno}:{key.value}")

        self.assertEqual(violations, [])

    def test_active_python_source_does_not_use_verbose_utc_time_field_names(self) -> None:
        forbidden = (
            "createdAtUtc",
            "updatedAtUtc",
            "occurredAtUtc",
            "lastRegistryUpdatedAtUtc",
            "lastDoctorRunAtUtc",
            "lastMigrationAtUtc",
            "startedAtUtc",
            "completedAtUtc",
            "lastUsedAtUtc",
            "modifiedAtUtc",
            "observedAtUtc",
            "appliedAtUtc",
            "publishedAtUtc",
            "created_at_utc",
            "updated_at_utc",
            "occurred_at_utc",
            "last_registry_updated_at_utc",
            "last_doctor_run_at_utc",
            "last_migration_at_utc",
            "started_at_utc",
            "completed_at_utc",
            "last_used_at_utc",
            "modified_at_utc",
            "observed_at_utc",
            "applied_at_utc",
            "published_at_utc",
            "localCreatedAt",
            "localUpdatedAt",
            "createdAtLocal",
            "updatedAtLocal",
        )
        violations: list[str] = []
        for path in (SRC / "ai_workroot").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), start=1):
                for term in forbidden:
                    index = line.find(term)
                    while index >= 0:
                        violations.append(f"{path.relative_to(ROOT)}:{lineno}:{term}:{line.strip()}")
                        index = line.find(term, index + 1)

        self.assertEqual(violations, [])

    def test_active_docs_do_not_describe_verbose_utc_time_field_names_as_current_contract(self) -> None:
        forbidden = (
            "createdAtUtc",
            "updatedAtUtc",
            "occurredAtUtc",
            "lastRegistryUpdatedAtUtc",
            "lastDoctorRunAtUtc",
            "lastMigrationAtUtc",
            "startedAtUtc",
            "completedAtUtc",
            "lastUsedAtUtc",
            "modifiedAtUtc",
            "observedAtUtc",
            "appliedAtUtc",
            "publishedAtUtc",
            "created_at_utc",
            "updated_at_utc",
            "occurred_at_utc",
            "last_registry_updated_at_utc",
            "last_doctor_run_at_utc",
            "last_migration_at_utc",
            "started_at_utc",
            "completed_at_utc",
            "last_used_at_utc",
            "modified_at_utc",
            "observed_at_utc",
            "applied_at_utc",
            "published_at_utc",
            "localCreatedAt",
            "localUpdatedAt",
            "createdAtLocal",
            "updatedAtLocal",
        )
        doc_roots = [ROOT / "docs/specs", ROOT / "docs/dev"]
        ignored_parts = {"history", "e2e-incidents"}
        violations: list[str] = []
        for root in doc_roots:
            for path in root.rglob("*.md"):
                relative_parts = set(path.relative_to(ROOT).parts)
                if relative_parts & ignored_parts:
                    continue
                text = path.read_text(encoding="utf-8")
                for lineno, line in enumerate(text.splitlines(), start=1):
                    for term in forbidden:
                        index = line.find(term)
                        while index >= 0:
                            violations.append(f"{path.relative_to(ROOT)}:{lineno}:{term}:{line.strip()}")
                            index = line.find(term, index + 1)

        self.assertEqual(violations, [])

    def test_runtime_state_does_not_contain_old_compatibility_layout(self) -> None:
        state_path = SRC / "ai_workroot" / "runtime" / "state.py"
        text = state_path.read_text(encoding="utf-8")
        forbidden = (
            "contextGuide",
            "knowledge/facts",
            "knowledge/inbox",
            "graph/exports",
            "graph/backups",
            "user/profile.md",
            "initialize_workroot_state_unlocked",
        )
        violations = [term for term in forbidden if term in text]

        self.assertEqual(violations, [])

    def test_active_source_does_not_use_sqlite_datetime_now_for_canonical_writes(self) -> None:
        violations: list[str] = []
        for path in (SRC / "ai_workroot").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "datetime('now')" in text:
                violations.append(path.relative_to(ROOT).as_posix())

        self.assertEqual(violations, [])


if __name__ == "__main__":
    sys.path.insert(0, str(SRC))
    unittest.main()


def _is_subprocess_run(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "run"
        and isinstance(func.value, ast.Name)
        and func.value.id == "subprocess"
    )


def _call_contains_scripts_path(node: ast.Call) -> bool:
    return any("scripts/" in value or "scripts\\" in value for value in _string_constants(node))


def _string_constants(node: ast.AST) -> Iterable[str]:
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            yield child.value


def _legacy_camel_time_key(prefix: str) -> str:
    return f"{prefix}At"


def _legacy_snake_time_key(prefix: str) -> str:
    return f"{prefix}_at"


def _quoted_ambiguous_timestamp(quote: str) -> str:
    return f"{quote}time" + f"stamp{quote}"
