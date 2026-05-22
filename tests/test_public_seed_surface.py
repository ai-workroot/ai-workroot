from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from ai_workroot.runtime.release_validation import is_git_ignored


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SEED = ROOT / "docs/history/public-seed"
TEXT_SUFFIXES = {".md", ".json", ".csv", ".py", ".yml", ".yaml", ".txt", ".sql"}
CURRENT_DOC_ROOTS = (
    ROOT / "README.md",
    ROOT / "ROADMAP.md",
    ROOT / "START_HERE_FOR_HUMANS.md",
    ROOT / "docs",
)
HISTORICAL_DOC_PREFIXES = (
    ROOT / "docs/history",
    ROOT / "docs/releases",
    ROOT / "docs/incidents",
)
NOVICE_INTERNAL_TERMS = [
    ".workroot",
    "kernel",
    "registry",
    "schema",
    "runtime",
]
FORBIDDEN_TEXT_PATTERNS = [
    ".".join(["0", "9", "0"]),
    "v" + ".".join(["0", "9", "0"]),
    "Un" + "released",
    "actor" + "_" + "registry",
    "owner" + "_" + "id",
    "parent" + "_" + "task" + "_" + "id",
    "migrate" + "_" + "workroot",
    "validate" + "_" + "workroot",
    "migration" + "_" + "registry",
    "migration" + "-" + "policy",
]


class PublicSeedSurfaceTest(unittest.TestCase):
    def test_clean_workroot_root_surface(self) -> None:
        allowed = {
            ".github",
            ".gitignore",
            "AUTHOR.md",
            "CHANGELOG.md",
            "CONTRIBUTING.md",
            "DCO.md",
            "LICENSE",
            "NOTICE",
            "PROJECT_BRIEF.md",
            "pyproject.toml",
            "README.md",
            "ROADMAP.md",
            "START_HERE_FOR_HUMANS.md",
            "TRADEMARKS.md",
            "assets",
            "docs",
            "install",
            "scripts",
            "src",
            "tests",
            "workroot.project.json",
        }
        present = {path.name for path in ROOT.iterdir() if path.name != ".git" and not is_git_ignored(ROOT, path)}
        self.assertEqual(present - allowed, set())
        self.assertFalse({"AGENTS.md", "CLAUDE.md", "space", ".workroot"} & present)

    def test_release_validation(self) -> None:
        result = subprocess.run(
            [str(ROOT / "scripts/dev/validate-release.sh")],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Clean Workroot release validation passed", result.stdout)

    def test_public_seed_does_not_use_status_task_directories(self) -> None:
        self.assertFalse((PUBLIC_SEED / ".workroot/runtime/work/active").exists())
        self.assertFalse((PUBLIC_SEED / ".workroot/runtime/work/closed").exists())
        self.assertTrue((PUBLIC_SEED / ".workroot/runtime/work/tasks").is_dir())

    def test_no_stale_public_text_patterns(self) -> None:
        hits: list[str] = []
        for path in ROOT.rglob("*"):
            if ".git" in path.parts or not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if path == Path(__file__):
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in FORBIDDEN_TEXT_PATTERNS:
                if pattern in text:
                    hits.append(f"{path.relative_to(ROOT).as_posix()}: {pattern}")
        self.assertEqual(hits, [])

    def test_current_docs_do_not_contain_local_absolute_paths(self) -> None:
        hits: list[str] = []
        for path in current_doc_files():
            text = path.read_text(encoding="utf-8")
            if "/Users/" in text:
                hits.append(path.relative_to(ROOT).as_posix())

        self.assertEqual(hits, [])

    def test_current_docs_do_not_present_old_script_paths_as_active_workflow(self) -> None:
        hits: list[str] = []
        for path in current_doc_files():
            text = path.read_text(encoding="utf-8")
            if "scripts/workroot_" in text or "python3 scripts/workroot_" in text or "python scripts/workroot_" in text:
                hits.append(path.relative_to(ROOT).as_posix())

        self.assertEqual(hits, [])

    def test_start_here_starts_with_one_sentence_path(self) -> None:
        first_sentence = "I want this Workroot to help me with [area]. Please set it up with me, then help me start my first real task."
        text = (ROOT / "START_HERE_FOR_HUMANS.md").read_text(encoding="utf-8")
        position = text.find(first_sentence)
        self.assertGreaterEqual(position, 0)
        self.assertLess(position, 700)

    def test_readme_points_ordinary_users_to_start_here(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        position = text.find("START_HERE_FOR_HUMANS.md")
        self.assertGreaterEqual(position, 0)
        self.assertLess(position, 1200)

    def test_primary_docs_do_not_present_public_seed_as_current_architecture(self) -> None:
        forbidden = (
            "Current Public Seed",
            "P0 - Stabilize The Public Seed",
            "The public architecture is:",
            "The public seed must use the upgraded architecture",
            "The public layout is:",
            "current public seed architecture",
        )
        for rel in (
            "README.md",
            "ROADMAP.md",
            "docs/architecture.md",
            "docs/architecture-map.md",
            "docs/workroot-system-design.md",
            "docs/kernel-implementation-specification.md",
        ):
            with self.subTest(rel=rel):
                text = (ROOT / rel).read_text(encoding="utf-8")
                for phrase in forbidden:
                    self.assertNotIn(phrase, text)

    def test_primary_docs_describe_clean_workroot_current_architecture(self) -> None:
        docs = {
            "README.md": ("Clean Workroot", "AI_WORKROOT_HOME", "Public Seed is historical"),
            "ROADMAP.md": ("Clean Workroot", "0.9.530", "Public Seed is historical"),
            "docs/architecture-map.md": ("Clean Workroot", "WorkrootEnvironment", "Relationship Network"),
            "docs/workroot-system-design.md": ("Clean Workroot", "AI_WORKROOT_HOME", "Native Agent Entry"),
            "docs/kernel-implementation-specification.md": ("Clean Workroot", "Core / Contracts / Runtime / Storage / Indexing / Agent / CLI", "Release Control"),
        }
        for rel, phrases in docs.items():
            with self.subTest(rel=rel):
                text = (ROOT / rel).read_text(encoding="utf-8")
                for phrase in phrases:
                    self.assertIn(phrase, text)

    def test_scripts_to_src_migration_closure_is_explicit(self) -> None:
        text = (ROOT / "docs/dev/runnable-legacy-compat-removal-architecture.md").read_text(
            encoding="utf-8"
        )
        archive_manifest = (ROOT / "docs/history/public-seed/code-archive/MANIFEST.md").read_text(encoding="utf-8")
        script_rows = [
            [cell.strip() for cell in row.strip("|").split("|")]
            for row in (ROOT / "docs/dev/0.9.530/scripts-to-src-migration.md").read_text(encoding="utf-8").splitlines()
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
            self.assertIn(cells[3], {"migrated", "wrapper", "dev-helper", "legacy-quarantine", "retired", "deferred", "release validation helper"}, cells)
        actual_scripts = {
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "scripts").rglob("*")
            if path.is_file()
        }
        self.assertEqual(actual_scripts, {"scripts/README.md", "scripts/dev/README.md", "scripts/dev/bootstrap-dev.ps1", "scripts/dev/bootstrap-dev.sh", "scripts/dev/export-review-zip.sh", "scripts/dev/validate-release.sh"})

    def test_scripts_root_has_no_python_product_or_compat_files(self) -> None:
        root_python = sorted(path.name for path in (ROOT / "scripts").glob("*.py"))
        self.assertEqual(root_python, [])

    def test_scripts_subdirectories_make_roles_explicit(self) -> None:
        self.assertTrue((ROOT / "scripts/dev/README.md").is_file())
        self.assertFalse((ROOT / "scripts/compat").exists())
        self.assertFalse((ROOT / "scripts/legacy").exists())

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
            "docs/dev/0.9.530/README.md",
            "docs/dev/0.9.530/final-compatibility-preserving-script-migration-design.md",
            "docs/dev/0.9.530/scripts-to-src-migration.md",
            "docs/dev/0.9.530/scripts-to-src-migration-architecture.md",
            "docs/dev/0.9.530/scripts-to-src-migration-detailed-design.md",
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

    def test_readme_uses_current_domain_terms_for_formal_foundation(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        start = text.index("In practical terms, AI Workroot gives agents a shared, user-owned foundation for:")
        end = text.index("The folders, registries, schemas, and validation scripts are implementation details.")
        formal_section = text[start:end]

        for phrase in (
            "Workroot Management",
            "Work",
            "Assets",
            "Release Control",
            "Relationship Network",
            "Retrieval & Index Control",
            "Context Control",
            "Agent Interface",
            "System Health",
        ):
            self.assertIn(phrase, formal_section)
        for retired in ("task state", "memory", "Mind", "Context Guide", "Context Gate"):
            self.assertNotIn(retired, formal_section)

    def test_active_public_docs_do_not_use_public_seed_paths_as_current_workflow(self) -> None:
        docs = (
            "docs/product-experience.md",
            "docs/daily-loop.md",
            "docs/instantiate-workroot.md",
            "docs/user-interaction-contract.md",
            "docs/product-hardening.md",
            "docs/scaling-and-longevity.md",
            "docs/extension-contract.md",
        )
        forbidden = (
            "visible user-owned space is `space/`",
            "system kernel lives under `.workroot/`",
            "write the minimum guidance into `space/profile/`",
            "Save the guidance in `space/profile/`",
            "maintain `space/work/continue.md`",
            "Human Continuation View\n\nAI Workroot should maintain a user-facing continuation view at:\n\n```text\nspace/work/continue.md",
            "preserve outputs in `space/work/`",
            "preserve reusable understanding in `space/mind/`",
            "user-facing outputs land in `space/work/`",
            "reusable understanding lands in `space/mind/`",
            "files under `.workroot/extensions/capabilities/<capability-id>/`",
            "move durable knowledge out of `space/mind/`",
            "See `.workroot/kernel/config/`",
            "Do not rename internal protocol folders such as `space`, `.workroot`, or `docs`.",
        )
        for rel in docs:
            with self.subTest(rel=rel):
                text = (ROOT / rel).read_text(encoding="utf-8")
                for phrase in forbidden:
                    self.assertNotIn(phrase, text)

    def test_human_entry_does_not_expose_registry_paths(self) -> None:
        for rel in ("README.md", "START_HERE_FOR_HUMANS.md"):
            with self.subTest(rel=rel):
                text = (ROOT / rel).read_text(encoding="utf-8")
                self.assertNotIn(".workroot/runtime/index", text)
                self.assertNotIn("link_registry.csv", text)

    def test_start_here_first_screen_is_novice_safe(self) -> None:
        text = (ROOT / "START_HERE_FOR_HUMANS.md").read_text(encoding="utf-8")[:1500].lower()
        for term in NOVICE_INTERNAL_TERMS:
            with self.subTest(term=term):
                self.assertNotIn(term, text)

    def test_user_visible_work_files_do_not_expose_internal_terms(self) -> None:
        hits: list[str] = []
        for path in (PUBLIC_SEED / "space/work").rglob("*.md"):
            text = path.read_text(encoding="utf-8").lower()
            for term in NOVICE_INTERNAL_TERMS:
                if term in text:
                    hits.append(f"{path.relative_to(ROOT).as_posix()}: {term}")
        self.assertEqual(hits, [])

    def test_novice_task_language_exists(self) -> None:
        combined = "\n".join(
            (ROOT / rel).read_text(encoding="utf-8")
            for rel in (
                "README.md",
                "START_HERE_FOR_HUMANS.md",
                "docs/user-sop.md",
                "docs/user-interaction-contract.md",
            )
        )
        self.assertIn("A task is just the thing you are working on now.", combined)
        self.assertIn("Help me continue.", combined)
        self.assertIn("This task is finished. Save what matters and help me start a new task.", combined)
        self.assertIn("What tasks have I done before?", combined)
        self.assertIn("answer in the language", combined)


def current_doc_files() -> list[Path]:
    files: list[Path] = []
    for root in CURRENT_DOC_ROOTS:
        if root.is_file():
            candidates = [root]
        else:
            candidates = [path for path in root.rglob("*") if path.is_file()]
        for path in candidates:
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if any(_is_relative_to(path, historical) for historical in HISTORICAL_DOC_PREFIXES):
                continue
            files.append(path)
    return sorted(set(files))


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    unittest.main()
