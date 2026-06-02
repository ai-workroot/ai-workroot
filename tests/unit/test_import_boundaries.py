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
            "agent_entry",
            "assets",
            "commands",
            "context",
            "diagnostics",
            "handoff",
            "protocol",
            "relationships",
            "release",
            "retrieval",
            "shared",
            "state",
            "cli",
            "templates",
            "work",
        ]

        for name in required:
            with self.subTest(name=name):
                self.assertTrue((SRC / "ai_workroot" / name / "__init__.py").is_file())

    def test_legacy_compatibility_package_directories_do_not_exist(self) -> None:
        forbidden = [
            "agent",
            "contracts",
            "core",
            "indexing",
            "resources",
            "runtime",
            "storage",
        ]

        for name in forbidden:
            with self.subTest(name=name):
                self.assertFalse((SRC / "ai_workroot" / name).exists())

    def test_tests_root_contains_no_loose_test_modules(self) -> None:
        loose_tests = sorted(path.relative_to(ROOT).as_posix() for path in (ROOT / "tests").glob("test_*.py"))

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

    def test_active_python_source_uses_ascii_only(self) -> None:
        violations: list[str] = []
        for path in (SRC / "ai_workroot").rglob("*.py"):
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if any(ord(char) > 127 for char in line):
                    violations.append(f"{path.relative_to(ROOT)}:{line_number}")

        self.assertEqual(violations, [])

    def test_protocol_focus_has_no_natural_language_marker_tables(self) -> None:
        path = SRC / "ai_workroot" / "protocol" / "focus.py"
        source = path.read_text(encoding="utf-8")
        forbidden = (
            "DURABLE_MARKERS",
            "CONTINUATION_MARKERS",
            "GUARDED_MARKERS",
            "_contains_any",
            "_has_start_boundary",
        )

        self.assertEqual([name for name in forbidden if name in source], [])

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

    def test_shared_contracts_do_not_import_project_modules(self) -> None:
        contracts_dir = SRC / "ai_workroot" / "shared" / "contracts"
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

    def test_src_does_not_import_legacy_architecture_namespaces(self) -> None:
        forbidden = (
            "ai_workroot.agent",
            "ai_workroot.contracts",
            "ai_workroot.core",
            "ai_workroot.indexing",
            "ai_workroot.resources",
            "ai_workroot.runtime",
            "ai_workroot.storage",
        )
        violations: list[str] = []

        for path in (SRC / "ai_workroot").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if _module_matches_any(alias.name, forbidden):
                            violations.append(f"{path.relative_to(ROOT)} imports {alias.name}")
                elif isinstance(node, ast.ImportFrom) and node.module:
                    if _module_matches_any(node.module, forbidden):
                        violations.append(f"{path.relative_to(ROOT)} imports from {node.module}")

        self.assertEqual(violations, [])

    def test_package_dependency_graph_is_acyclic_and_declared(self) -> None:
        allowed_edges = {
            "agent_entry": set(),
            "assets": {"state"},
            "cli": {"commands"},
            "commands": {"agent_entry", "context", "diagnostics", "protocol", "state"},
            "context": {"protocol", "relationships", "release", "retrieval", "state"},
            "diagnostics": {"agent_entry", "state"},
            "handoff": {"state"},
            "protocol": {"state"},
            "relationships": {"state"},
            "release": set(),
            "retrieval": {"state"},
            "shared": set(),
            "state": set(),
            "templates": set(),
            "work": {"state"},
        }
        edges = _package_dependency_edges()
        unexpected = sorted(
            f"{source} -> {target}"
            for source, targets in edges.items()
            for target in targets
            if target not in allowed_edges[source]
        )

        self.assertEqual(unexpected, [])
        self.assertEqual(_package_dependency_cycles(edges), [])

    def test_domain_packages_do_not_import_protocol(self) -> None:
        forbidden = ("ai_workroot.protocol",)
        violations: list[str] = []
        for package in ("work", "assets", "handoff"):
            for path in (SRC / "ai_workroot" / package).rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                for module in _imported_project_modules(tree):
                    if _module_matches_any(module, forbidden):
                        violations.append(f"{path.relative_to(ROOT)} imports {module}")

        self.assertEqual(violations, [])

    def test_protocol_package_does_not_import_cli(self) -> None:
        violations: list[str] = []
        for path in (SRC / "ai_workroot" / "protocol").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for module in _imported_project_modules(tree):
                if _module_matches_any(module, ("ai_workroot.cli",)):
                    violations.append(f"{path.relative_to(ROOT)} imports {module}")

        self.assertEqual(violations, [])

    def test_agent_exchange_command_does_not_import_sqlite(self) -> None:
        path = SRC / "ai_workroot" / "commands" / "agent_exchange.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        violations: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "sqlite3":
                        violations.append(f"{path.relative_to(ROOT)} imports sqlite3")
            elif isinstance(node, ast.ImportFrom) and node.module == "sqlite3":
                violations.append(f"{path.relative_to(ROOT)} imports from sqlite3")

        self.assertEqual(violations, [])

    def test_shared_model_bucket_does_not_exist(self) -> None:
        self.assertFalse((SRC / "ai_workroot" / "shared" / "model.py").exists())

    def test_retrieval_does_not_own_release_filtering(self) -> None:
        retrieval_dir = SRC / "ai_workroot" / "retrieval"
        self.assertFalse((retrieval_dir / "providers" / "release_provider.py").exists())
        forbidden_symbols = (
            "ReleaseFilterReport",
            "FtsReleaseFilterReport",
            "RelationshipReleaseFilterReport",
            "CandidateReleaseTargetResolver",
            "load_release_filter_report",
            "filter_fts_matches_for_release",
            "filter_relationship_signals_for_release",
        )
        violations: list[str] = []

        for path in retrieval_dir.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for symbol in forbidden_symbols:
                if symbol in text:
                    violations.append(f"{path.relative_to(ROOT)} defines or references {symbol}")
            tree = ast.parse(text, filename=str(path))
            for module in _imported_project_modules(tree):
                if _module_matches_any(module, ("ai_workroot.release",)):
                    violations.append(f"{path.relative_to(ROOT)} imports {module}")

        self.assertEqual(violations, [])

    def test_retrieval_does_not_expose_unfiltered_context_recall_hint_materializers(self) -> None:
        from ai_workroot.retrieval.providers import context_recall_hint_provider

        self.assertFalse(hasattr(context_recall_hint_provider, "materialize_context_recall_hint"))
        self.assertFalse(hasattr(context_recall_hint_provider, "materialize_context_recall_hints"))

    def test_context_builder_uses_explicit_assembly_pipeline(self) -> None:
        builder_path = SRC / "ai_workroot" / "context" / "builder.py"
        tree = ast.parse(builder_path.read_text(encoding="utf-8"), filename=str(builder_path))
        class_names = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
        expected_stage_models = {
            "ContextRuntime",
            "LoadedContext",
            "RetrievedContext",
            "GovernedContext",
            "SelectedContext",
            "RenderedContext",
        }
        function_by_name = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
        expected_stage_functions = [
            "_resolve_context_runtime",
            "_load_context_state",
            "_prepare_recall_hints",
            "_retrieve_context",
            "_govern_context",
            "_select_context",
            "_apply_fallback_selection",
            "_render_context",
            "_apply_context_budget",
            "_record_context_result",
        ]

        self.assertTrue(expected_stage_models.issubset(class_names))
        self.assertTrue(set(expected_stage_functions).issubset(function_by_name))

        build_context_package = function_by_name["build_context_package"]
        call_lines = {
            node.func.id: node.lineno
            for node in ast.walk(build_context_package)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        ordered_lines = [call_lines[name] for name in expected_stage_functions]

        self.assertEqual(ordered_lines, sorted(ordered_lines))
        self.assertLessEqual(build_context_package.end_lineno - build_context_package.lineno + 1, 90)

    def test_cli_does_not_import_storage_or_indexing_directly(self) -> None:
        cli_dir = SRC / "ai_workroot" / "cli"
        forbidden = (
            "ai_workroot.storage",
            "ai_workroot.indexing",
            "ai_workroot.state",
            "ai_workroot.retrieval",
            "ai_workroot.runtime",
        )

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
        environment_path = SRC / "ai_workroot" / "state" / "environment.py"
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

    def test_state_package_does_not_contain_old_compatibility_layout(self) -> None:
        texts = "\n".join(path.read_text(encoding="utf-8") for path in (SRC / "ai_workroot" / "state").rglob("*.py"))
        forbidden = (
            "contextGuide",
            "knowledge/facts",
            "knowledge/inbox",
            "graph/exports",
            "graph/backups",
            "user/profile.md",
            "initialize_workroot_state_unlocked",
        )
        violations = [term for term in forbidden if term in texts]

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


def _module_matches_any(module: str, roots: tuple[str, ...]) -> bool:
    return any(module == root or module.startswith(root + ".") for root in roots)


def _package_dependency_edges() -> dict[str, set[str]]:
    package_root = SRC / "ai_workroot"
    packages = {
        path.name
        for path in package_root.iterdir()
        if path.is_dir() and (path / "__init__.py").is_file() and path.name != "__pycache__"
    }
    edges: dict[str, set[str]] = {package: set() for package in packages}
    for path in package_root.rglob("*.py"):
        relative = path.relative_to(package_root)
        if len(relative.parts) < 2:
            continue
        source_package = relative.parts[0]
        if source_package not in packages:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for module in _imported_project_modules(tree):
            parts = module.split(".")
            if len(parts) < 2 or parts[0] != "ai_workroot":
                continue
            target_package = parts[1]
            if target_package in packages and target_package != source_package:
                edges[source_package].add(target_package)
    return edges


def _imported_project_modules(tree: ast.AST) -> Iterable[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("ai_workroot."):
                    yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if node.module.startswith("ai_workroot."):
                yield node.module


def _package_dependency_cycles(edges: dict[str, set[str]]) -> list[str]:
    cycles: list[list[str]] = []

    def visit(start: str, node: str, path: list[str]) -> None:
        for target in edges[node]:
            if target == start:
                cycles.append([*path, target])
            elif target not in path:
                visit(start, target, [*path, target])

    for package in sorted(edges):
        visit(package, package, [package])

    unique: dict[str, list[str]] = {}
    for cycle in cycles:
        body = cycle[:-1]
        key = min(" -> ".join([*body[index:], *body[:index]]) for index in range(len(body)))
        unique.setdefault(key, cycle)
    return sorted(" -> ".join(cycle) for cycle in unique.values())


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
