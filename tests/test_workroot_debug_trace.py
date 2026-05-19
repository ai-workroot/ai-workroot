from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.workroot_candidates import ContextCandidate, upsert_context_candidate
from scripts.workroot_context import ContextRequest, build_context_package, write_debug_trace
from scripts.workroot_indexing import index_text_file
from scripts.workroot_sqlite import initialize_workroot_sqlite, open_sqlite
from scripts.workroot_state import initialize_workroot_state


class WorkrootDebugTraceTest(unittest.TestCase):
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
        db_path = initialized.state_directory / "indexes/workroot.sqlite"
        initialize_workroot_sqlite(db_path)
        with open_sqlite(db_path) as conn:
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_active",
                    workroot_id="wr_demo",
                    source_type="decision",
                    source_id="decision-1",
                    title="Active",
                    summary="Active context.",
                    importance="high",
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_never",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="knowledge-1",
                    title="Never auto",
                    summary="Private context.",
                    context_policy="never-auto",
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
                    title="Stale",
                    summary="Stale context.",
                    status="stale",
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )
            doc = user_dir / "notes.md"
            doc.write_text("# Notes\nActive context is searchable.\n", encoding="utf-8")
            index_text_file(conn, "wr_demo", user_dir, doc, indexed_at="2026-05-19T00:00:00Z")
        return home, user_dir, initialized.state_directory

    def test_debug_context_writes_trace_with_selection_and_retrieval_details(self) -> None:
        home, user_dir, state_dir = self.create_fixture()

        build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="active",
                debug=True,
                now="2026-05-19T00:00:00Z",
            )
        )

        latest = state_dir / "context/debug/latest.json"
        self.assertTrue(latest.exists())
        trace = json.loads(latest.read_text(encoding="utf-8"))
        for key in (
            "resolution",
            "challengers",
            "selectedCandidates",
            "droppedCandidates",
            "ftsMatches",
            "tokenBudget",
            "latencyMs",
        ):
            self.assertIn(key, trace)
        self.assertEqual(trace["resolution"]["workrootId"], "wr_demo")
        self.assertEqual(trace["challengers"][0]["name"], "current-state")
        self.assertEqual(trace["selectedCandidates"][0]["candidateId"], "cand_active")
        dropped = {item["candidateId"]: item["reason"] for item in trace["droppedCandidates"]}
        self.assertEqual(dropped["cand_never"], "never-auto")
        self.assertEqual(dropped["cand_stale"], "stale")
        self.assertEqual(trace["ftsMatches"][0]["relativePath"], "notes.md")

    def test_debug_trace_history_prunes_beyond_retention(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            debug_dir = Path(tmp)
            for i in range(55):
                trace = {
                    "traceId": f"trace_{i:02d}",
                    "schemaVersion": "0.9.529",
                    "latencyMs": i,
                }
                write_debug_trace(debug_dir, trace, retention=50)

            history = sorted((debug_dir / "history").glob("*.json"))

            self.assertEqual(len(history), 50)
            self.assertFalse((debug_dir / "history/trace_00.json").exists())
            self.assertTrue((debug_dir / "history/trace_54.json").exists())


if __name__ == "__main__":
    unittest.main()
