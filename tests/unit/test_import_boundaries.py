from __future__ import annotations

import ast
import sys
import unittest
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


if __name__ == "__main__":
    sys.path.insert(0, str(SRC))
    unittest.main()
