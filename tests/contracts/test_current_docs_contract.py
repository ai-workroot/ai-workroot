from __future__ import annotations

import unittest

from tests.contracts.helpers import NOVICE_INTERNAL_TERMS, PUBLIC_SEED, ROOT, current_doc_files


class CurrentDocsContractTest(unittest.TestCase):
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
            "docs/kernel-implementation-specification.md": (
                "Clean Workroot",
                "Core / Contracts / Runtime / Storage / Indexing / Agent / CLI",
                "Release Control",
            ),
        }
        for rel, phrases in docs.items():
            with self.subTest(rel=rel):
                text = (ROOT / rel).read_text(encoding="utf-8")
                for phrase in phrases:
                    self.assertIn(phrase, text)

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


if __name__ == "__main__":
    unittest.main()
