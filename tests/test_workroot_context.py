from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.workroot_candidates import ContextCandidate, upsert_context_candidate
from scripts.workroot_context import ContextRequest, build_context_package
from scripts.workroot_indexing import index_text_file
from scripts.workroot_sqlite import initialize_workroot_sqlite, open_sqlite
from scripts.workroot_state import initialize_workroot_state, write_json


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/workroot_cli.py"


class WorkrootContextTest(unittest.TestCase):
    def create_fixture(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        home = base / "home"
        user_dir = base / "project"
        user_dir.mkdir()
        initialized = initialize_workroot_state(
            home,
            "wr_demo",
            "Demo",
            user_dir,
            now="2026-05-19T00:00:00Z",
        )
        write_json(
            initialized.state_directory / "state/current.json",
            {
                "currentFocus": "Ship Clean Mode and local Context Guide.",
                "activeTaskId": "task-1",
                "nextSuggestedAction": "Run doctor and context verification.",
                "contextVersion": 1,
                "lastActivityAt": "2026-05-19T00:00:00Z",
            },
        )
        db_path = initialized.state_directory / "indexes/workroot.sqlite"
        initialize_workroot_sqlite(db_path)
        with open_sqlite(db_path) as conn:
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_clean_mode",
                    workroot_id="wr_demo",
                    source_type="decision",
                    source_id="decision-1",
                    title="Clean Mode decision",
                    summary="Managed state stays outside user-selected directories.",
                    importance="high",
                    confidence=0.95,
                    context_policy="always",
                    token_estimate=12,
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_stale",
                    workroot_id="wr_demo",
                    source_type="decision",
                    source_id="decision-old",
                    title="Stale decision",
                    summary="Old behavior.",
                    status="stale",
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_never",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="secret-1",
                    title="Manual only private note",
                    summary="Do not include automatically.",
                    context_policy="never-auto",
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )
            doc = user_dir / "notes.md"
            doc.write_text(
                "# Retrieval Notes\nLocal FTS should explain why clean mode context was selected.\n",
                encoding="utf-8",
            )
            index_text_file(conn, "wr_demo", user_dir, doc, indexed_at="2026-05-19T00:00:00Z")
            conn.execute(
                """
                INSERT INTO graph_nodes (
                  node_id, node_type, kind, title, summary, status, importance, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "decision-1",
                    "decision",
                    "architecture",
                    "Clean Mode",
                    "Clean Mode protects user directories.",
                    "active",
                    "high",
                    "2026-05-19T00:00:00Z",
                    "2026-05-19T00:00:00Z",
                ),
            )
            conn.commit()
        return home, user_dir, initialized.state_directory

    def test_build_context_package_uses_local_state_candidates_fts_and_graph(self) -> None:
        home, user_dir, state_dir = self.create_fixture()

        package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="clean mode",
                now="2026-05-19T00:00:00Z",
            )
        )

        self.assertIn("# AI Workroot Context Package", package.markdown)
        self.assertIn("## Current State", package.markdown)
        self.assertIn("Ship Clean Mode", package.markdown)
        self.assertIn("## Selected Context", package.markdown)
        self.assertIn("Clean Mode decision", package.markdown)
        self.assertIn("## FTS Matches", package.markdown)
        self.assertIn("notes.md", package.markdown)
        self.assertIn("## Graph Signals", package.markdown)
        self.assertIn("Clean Mode protects user directories", package.markdown)
        self.assertNotIn("Stale decision", package.markdown)
        self.assertNotIn("Manual only private note", package.markdown)
        self.assertTrue((state_dir / "context/packages/latest.md").exists())
        self.assertFalse((user_dir / ".workroot").exists())
        self.assertFalse((user_dir / ".ai-workroot").exists())
        self.assertFalse((user_dir / "context").exists())

    def test_cli_context_prints_markdown_package(self) -> None:
        home, user_dir, _ = self.create_fixture()

        result = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "context",
                "--agent",
                "codex",
                "--cwd",
                str(user_dir),
                "--query",
                "clean mode",
            ],
            cwd=ROOT,
            env={**os.environ, "AI_WORKROOT_HOME": str(home)},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("# AI Workroot Context Package", result.stdout)
        self.assertIn("Clean Mode decision", result.stdout)

    def test_cli_context_after_init_uses_initialized_sqlite_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            env = {**os.environ, "AI_WORKROOT_HOME": str(home)}
            init = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "init",
                    "--name",
                    "Demo",
                    "--directory",
                    str(user_dir),
                    "--no-native-agent-entry",
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            result = subprocess.run(
                [sys.executable, str(CLI), "context", "--agent", "codex", "--cwd", str(user_dir)],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("# AI Workroot Context Package", result.stdout)


if __name__ == "__main__":
    unittest.main()
