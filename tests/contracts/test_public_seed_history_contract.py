from __future__ import annotations

import unittest

from tests.contracts.helpers import PUBLIC_SEED, ROOT


class PublicSeedHistoryContractTest(unittest.TestCase):
    def test_public_seed_does_not_use_status_task_directories(self) -> None:
        self.assertFalse((PUBLIC_SEED / ".workroot/runtime/work/active").exists())
        self.assertFalse((PUBLIC_SEED / ".workroot/runtime/work/closed").exists())
        self.assertTrue((PUBLIC_SEED / ".workroot/runtime/work/tasks").is_dir())

    def test_archived_legacy_code_is_non_runnable_text(self) -> None:
        archive_root = ROOT / "docs/history/public-seed/code-archive"
        self.assertTrue((archive_root / "MANIFEST.md").is_file())
        runnable_archive_paths = [
            path.relative_to(ROOT).as_posix()
            for path in archive_root.rglob("*")
            if path.is_file() and path.name != "MANIFEST.md" and path.suffix != ".txt"
        ]

        self.assertEqual(runnable_archive_paths, [])

    def test_part2_means_capability_parity_not_compatibility_removal(self) -> None:
        docs = (
            "docs/history/0.9.530/dev/README.md",
            "docs/history/0.9.530/dev/final-compatibility-preserving-script-migration-design.md",
            "docs/history/0.9.530/dev/scripts-to-src-migration.md",
            "docs/history/0.9.530/dev/scripts-to-src-migration-architecture.md",
            "docs/history/0.9.530/dev/scripts-to-src-migration-detailed-design.md",
            "docs/specs/031-compatibility-preserving-script-migration.spec.md",
            "docs/specs/032-part2-capability-parity-small-specs.spec.md",
            "docs/specs/033-time-and-global-index-parity.spec.md",
        )
        forbidden = (
            "Part 2 removes",
            "Part 2 remove",
            "Part 2 may remove",
            "Part 2 must have its own branch",
            "Part 2 is a later branch/version",
            "future Part 2",
            "Part 2 path for compatibility removal",
        )
        for rel in docs:
            with self.subTest(rel=rel):
                text = (ROOT / rel).read_text(encoding="utf-8")
                for phrase in forbidden:
                    self.assertNotIn(phrase, text)
        self.assertIn(
            "Part 2 capability parity",
            (ROOT / "docs/specs/032-part2-capability-parity-small-specs.spec.md").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "Compatibility Removal phase",
            (ROOT / "docs/specs/031-compatibility-preserving-script-migration.spec.md").read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
