from __future__ import annotations

import ast
import unittest

from tests.contracts.helpers import ROOT


class DependencyPolicyContractTest(unittest.TestCase):
    def test_p0_code_paths_do_not_require_vector_or_remote_embeddings(self) -> None:
        p0_files = [
            "src/ai_workroot/commands/bootstrap_dev.py",
            "src/ai_workroot/commands/init_workroot.py",
            "src/ai_workroot/context/builder.py",
            "src/ai_workroot/diagnostics/doctor.py",
            "src/ai_workroot/state/layout.py",
            "src/ai_workroot/state/environment.py",
            "src/ai_workroot/state/sqlite.py",
            "src/ai_workroot/retrieval/providers/sqlite_fts.py",
            "src/ai_workroot/cli/main.py",
        ]
        forbidden_import_roots = {"openai", "requests", "httpx", "chromadb", "faiss"}
        forbidden_calls = {"Embedding", "embeddings"}

        for rel in p0_files:
            tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported = {alias.name.split(".")[0] for alias in node.names}
                    self.assertFalse(imported & forbidden_import_roots, f"{rel} imports {imported}")
                if isinstance(node, ast.ImportFrom) and node.module:
                    self.assertNotIn(node.module.split(".")[0], forbidden_import_roots, rel)
                if isinstance(node, ast.Attribute):
                    self.assertNotIn(node.attr, forbidden_calls, rel)


if __name__ == "__main__":
    unittest.main()
