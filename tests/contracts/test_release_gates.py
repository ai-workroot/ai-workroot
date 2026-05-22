from __future__ import annotations

import unittest

from tests.contracts.helpers import PUBLIC_SEED, ROOT


ARCHIVE = ROOT / "docs/history/public-seed/code-archive"


class ReleaseGates0529Test(unittest.TestCase):
    def test_rebuild_sqlite_is_archived_as_non_runnable_legacy_tooling(self) -> None:
        script = (ARCHIVE / "scripts/legacy/public_seed/rebuild_sqlite.py.txt").read_text(encoding="utf-8")
        instantiate = (ROOT / "docs/instantiate-workroot.md").read_text(encoding="utf-8")

        self.assertIn("Legacy public-seed SQLite rebuild tool", script)
        self.assertIn("legacy public seed", instantiate)
        self.assertNotIn("Clean Mode users should run `python3 scripts/legacy/public_seed/rebuild_sqlite.py`", instantiate)

    def test_release_notes_include_known_limitations(self) -> None:
        release_notes = (ROOT / "docs/releases/0.9.529.md").read_text(encoding="utf-8")

        for text in (
            "Windows PowerShell parse validation is pending",
            "install.sh is a CLI wrapper installer",
            "Quality Mode is currently labeled as quality-budget-expansion",
            "scripts/legacy/public_seed/rebuild_sqlite.py remains legacy public-seed tooling",
        ):
            self.assertIn(text, release_notes)

    def test_numbered_0529_specs_are_preserved_in_history(self) -> None:
        specs = ROOT / "docs/history/0.9.529/specs"
        expected = (
            "001-project-structure-and-naming.spec.md",
            "002-clean-mode-installation.spec.md",
            "003-managed-state-layout.spec.md",
            "004-bootstrap-process.spec.md",
            "005-migrations.spec.md",
            "006-doctor-command.spec.md",
            "007-context-guide-builder.spec.md",
            "008-materialized-context-candidates.spec.md",
            "009-fts-indexing-and-retrieval.spec.md",
            "010-debug-trace-and-observability.spec.md",
            "011-cli-user-flows.spec.md",
            "012-native-agent-entry.spec.md",
            "014-release-and-test-gates.spec.md",
        )

        for filename in expected:
            self.assertTrue((specs / filename).is_file(), filename)

    def test_context_amendment_release_gate_requirements_are_present(self) -> None:
        spec = (ROOT / "docs/history/0.9.529/specs/015-context-guide-modes-budgets-and-confidence.spec.md").read_text(
            encoding="utf-8"
        )
        checklist = (ROOT / "docs/release-checklist.md").read_text(encoding="utf-8")
        context_source = (ROOT / "src/ai_workroot/runtime/context.py").read_text(encoding="utf-8")


        self.assertIn("runtime-hints.json", spec)
        self.assertIn("Deep Mode requires explicit request", checklist)
        self.assertIn("Context Package includes mode, confidence, latency, token usage", checklist)
        self.assertIn("DEFAULT_TARGET_TOKENS", context_source)
        self.assertIn("DEFAULT_HARD_TOKEN_LIMIT", context_source)


if __name__ == "__main__":
    unittest.main()
