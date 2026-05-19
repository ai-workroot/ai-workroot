from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.workroot_candidates import (
    ContextCandidate,
    mark_candidate_status,
    mark_candidates_used,
    query_context_candidates,
    upsert_context_candidate,
)
from scripts.workroot_sqlite import initialize_workroot_sqlite, open_sqlite


class WorkrootCandidatesTest(unittest.TestCase):
    def open_db(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db_path = Path(tmp.name) / "workroot.sqlite"
        initialize_workroot_sqlite(db_path)
        return open_sqlite(db_path)

    def test_upsert_candidate_inserts_and_updates_record(self) -> None:
        with self.open_db() as conn:
            candidate = ContextCandidate(
                candidate_id="cand_decision_1",
                workroot_id="wr_demo",
                source_type="decision",
                source_id="decision-1",
                title="Clean Mode Decision",
                summary="Keep managed state outside user directories.",
                importance="high",
                confidence=0.9,
                status="active",
                context_policy="always",
                token_estimate=12,
                updated_at="2026-05-19T00:00:00Z",
            )
            upsert_context_candidate(conn, candidate)
            updated = ContextCandidate(
                candidate_id="cand_decision_1",
                workroot_id="wr_demo",
                source_type="decision",
                source_id="decision-1",
                title="Clean Mode Decision",
                summary="Clean Mode keeps generated state in AI Workroot home.",
                importance="high",
                confidence=0.95,
                status="active",
                context_policy="always",
                token_estimate=14,
                updated_at="2026-05-19T01:00:00Z",
            )
            upsert_context_candidate(conn, updated)

            rows = query_context_candidates(conn, "wr_demo")

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].summary, "Clean Mode keeps generated state in AI Workroot home.")
            self.assertEqual(rows[0].confidence, 0.95)

    def test_lifecycle_transitions_exclude_non_active_candidates(self) -> None:
        with self.open_db() as conn:
            for candidate_id in ("cand_stale", "cand_superseded", "cand_gravestone"):
                upsert_context_candidate(
                    conn,
                    ContextCandidate(
                        candidate_id=candidate_id,
                        workroot_id="wr_demo",
                        source_type="task",
                        source_id=candidate_id,
                        title=candidate_id,
                        summary="candidate",
                        updated_at="2026-05-19T00:00:00Z",
                    ),
                )
            mark_candidate_status(conn, "cand_stale", "stale", now="2026-05-19T01:00:00Z")
            mark_candidate_status(conn, "cand_superseded", "superseded", now="2026-05-19T01:00:00Z")
            mark_candidate_status(conn, "cand_gravestone", "gravestone", now="2026-05-19T01:00:00Z")

            rows = query_context_candidates(conn, "wr_demo")

            self.assertEqual(rows, [])

    def test_query_excludes_never_auto_candidates_by_default(self) -> None:
        with self.open_db() as conn:
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_auto",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="k1",
                    title="Auto",
                    summary="Selectable candidate",
                    context_policy="task-related",
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_never",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="k2",
                    title="Never",
                    summary="Manual only candidate",
                    context_policy="never-auto",
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )

            rows = query_context_candidates(conn, "wr_demo")

            self.assertEqual([row.candidate_id for row in rows], ["cand_auto"])

    def test_mark_candidates_used_updates_last_used_at(self) -> None:
        with self.open_db() as conn:
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_used",
                    workroot_id="wr_demo",
                    source_type="handoff",
                    source_id="handoff-1",
                    title="Handoff",
                    summary="Latest next action.",
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )
            mark_candidates_used(conn, ["cand_used"], now="2026-05-19T02:00:00Z")
            row = query_context_candidates(conn, "wr_demo")[0]

            self.assertEqual(row.last_used_at, "2026-05-19T02:00:00Z")


if __name__ == "__main__":
    unittest.main()
