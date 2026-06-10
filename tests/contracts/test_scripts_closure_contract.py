from __future__ import annotations

import unittest

from tests.contracts.helpers import ROOT


class ScriptsClosureContractTest(unittest.TestCase):
    def test_scripts_to_src_migration_closure_is_explicit(self) -> None:
        text = (ROOT / "docs/dev/runnable-legacy-compat-removal-architecture.md").read_text(encoding="utf-8")
        archive_manifest = (ROOT / "docs/history/public-seed/code-archive/MANIFEST.md").read_text(encoding="utf-8")
        migration_doc = ROOT / "docs/history/0.9.530/dev/scripts-to-src-migration.md"
        script_rows = [
            [cell.strip() for cell in row.strip("|").split("|")]
            for row in migration_doc.read_text(encoding="utf-8").splitlines()
            if row.startswith("| `scripts/")
        ]

        self.assertIn("Runnable Legacy Compatibility Removal", text)
        self.assertIn("scripts/compat/", text)
        self.assertIn("scripts/legacy/", text)
        self.assertIn("scripts/dev", text)
        self.assertIn("workroot_client.py.txt", archive_manifest)
        self.assertIn("legacy_context.py.txt", archive_manifest)
        self.assertIn("retired runnable Public Seed script", archive_manifest)
        for cells in script_rows:
            self.assertGreaterEqual(len(cells), 7, cells)
            self.assertIn(
                cells[3],
                {
                    "migrated",
                    "wrapper",
                    "dev-helper",
                    "legacy-quarantine",
                    "retired",
                    "deferred",
                    "release validation helper",
                },
                cells,
            )
        actual_scripts = {path.relative_to(ROOT).as_posix() for path in (ROOT / "scripts").rglob("*") if path.is_file()}
        self.assertEqual(
            actual_scripts,
            {
                "scripts/README.md",
                "scripts/dev/README.md",
                "scripts/dev/bootstrap-dev.ps1",
                "scripts/dev/bootstrap-dev.sh",
                "scripts/dev/export-review-zip.sh",
                "scripts/dev/setup-dev.sh",
                "scripts/dev/validate-release.sh",
            },
        )

    def test_scripts_root_has_no_python_product_or_compat_files(self) -> None:
        root_python = sorted(path.name for path in (ROOT / "scripts").glob("*.py"))
        self.assertEqual(root_python, [])

    def test_scripts_subdirectories_make_roles_explicit(self) -> None:
        self.assertTrue((ROOT / "scripts/dev/README.md").is_file())
        self.assertFalse((ROOT / "scripts/compat").exists())
        self.assertFalse((ROOT / "scripts/legacy").exists())


if __name__ == "__main__":
    unittest.main()
