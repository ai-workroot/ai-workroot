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

    def test_query_excludes_blocked_safety_policies_by_default(self) -> None:
        with self.open_db() as conn:
            candidates = [
                ContextCandidate(
                    candidate_id="cand_safe",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="k-safe",
                    title="Safe",
                    summary="Selectable candidate",
                    safety_policy="",
                    updated_at="2026-05-19T00:00:00Z",
                ),
                ContextCandidate(
                    candidate_id="cand_needs_confirmation",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="k-needs",
                    title="Needs confirmation",
                    summary="Should not be included by repository defaults",
                    safety_policy="needs-confirmation",
                    updated_at="2026-05-19T00:00:00Z",
                ),
                ContextCandidate(
                    candidate_id="cand_sensitive",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="k-sensitive",
                    title="Sensitive",
                    summary="Should not be included by repository defaults",
                    safety_policy="sensitive",
                    updated_at="2026-05-19T00:00:00Z",
                ),
                ContextCandidate(
                    candidate_id="cand_never_auto_safety",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="k-never-safety",
                    title="Never auto safety",
                    summary="Should not be included by repository defaults",
                    safety_policy="never-auto",
                    updated_at="2026-05-19T00:00:00Z",
                ),
            ]
            for candidate in candidates:
                upsert_context_candidate(conn, candidate)

            default_rows = query_context_candidates(conn, "wr_demo")
            audit_rows = query_context_candidates(conn, "wr_demo", include_blocked_safety=True)

            self.assertEqual([row.candidate_id for row in default_rows], ["cand_safe"])
            self.assertEqual(
                {row.candidate_id for row in audit_rows},
                {"cand_safe", "cand_needs_confirmation", "cand_sensitive", "cand_never_auto_safety"},
            )

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

    def test_mark_candidates_used_is_scoped_by_workroot_id(self) -> None:
        with self.open_db() as conn:
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_demo",
                    workroot_id="wr_demo",
                    source_type="handoff",
                    source_id="handoff-1",
                    title="Handoff",
                    summary="Latest next action.",
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_other",
                    workroot_id="wr_other",
                    source_type="handoff",
                    source_id="handoff-2",
                    title="Other Handoff",
                    summary="Other Workroot next action.",
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )

            mark_candidates_used(conn, "wr_demo", ["cand_demo", "cand_other"], now="2026-05-19T02:00:00Z")
            rows = conn.execute(
                "SELECT candidate_id, workroot_id, last_used_at, use_count FROM context_candidates ORDER BY candidate_id",
            ).fetchall()

            self.assertEqual(rows[0][0], "cand_demo")
            self.assertEqual(rows[0][1], "wr_demo")
            self.assertEqual(rows[0][2], "2026-05-19T02:00:00Z")
            self.assertEqual(rows[0][3], 1)
            self.assertEqual(rows[1][0], "cand_other")
            self.assertEqual(rows[1][1], "wr_other")
            self.assertEqual(rows[1][2], "")
            self.assertEqual(rows[1][3], 0)

    def test_selected_candidate_use_count_increments(self) -> None:
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
            mark_candidates_used(conn, ["cand_used"], now="2026-05-19T03:00:00Z")
            row = conn.execute(
                "SELECT last_used_at, use_count FROM context_candidates WHERE candidate_id = ?",
                ("cand_used",),
            ).fetchone()

            self.assertEqual(row[0], "2026-05-19T03:00:00Z")
            self.assertEqual(row[1], 2)

    def test_candidate_fts_indexes_domains(self) -> None:
        with self.open_db() as conn:
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_architecture",
                    workroot_id="wr_demo",
                    source_type="decision",
                    source_id="decision-architecture",
                    title="Context mode decision",
                    summary="Context Guide uses configurable budgets.",
                    domains="architecture retrieval",
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )

            columns = [row[1] for row in conn.execute("PRAGMA table_info(context_candidates_fts)").fetchall()]
            matches = conn.execute(
                "SELECT candidate_id FROM context_candidates_fts WHERE context_candidates_fts MATCH ?",
                ("architecture",),
            ).fetchall()

            self.assertIn("domains", columns)
            self.assertEqual(matches[0][0], "cand_architecture")

    def test_upsert_candidate_rebuilds_legacy_candidate_fts_without_domains(self) -> None:
        with self.open_db() as conn:
            conn.execute("DROP TABLE context_candidates_fts")
            conn.execute(
                """
                CREATE VIRTUAL TABLE context_candidates_fts USING fts5(
                  candidate_id,
                  title,
                  summary
                )
                """
            )
            conn.commit()

            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_legacy",
                    workroot_id="wr_demo",
                    source_type="decision",
                    source_id="decision-legacy",
                    title="Legacy FTS",
                    summary="Legacy table should be rebuilt.",
                    domains="retrieval",
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )

            columns = [row[1] for row in conn.execute("PRAGMA table_info(context_candidates_fts)").fetchall()]
            matches = conn.execute(
                "SELECT candidate_id FROM context_candidates_fts WHERE context_candidates_fts MATCH ?",
                ("retrieval",),
            ).fetchall()
            self.assertIn("domains", columns)
            self.assertEqual(matches[0][0], "cand_legacy")


if __name__ == "__main__":
    unittest.main()
