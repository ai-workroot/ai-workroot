from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
import json

from ai_workroot.indexing.providers.candidate_provider import upsert_context_candidate
from ai_workroot.indexing.providers.context_recall_hint_provider import ContextRecallHint, upsert_context_recall_hint
from ai_workroot.indexing.providers.relationship_provider import upsert_relationship_edge, upsert_relationship_node
from ai_workroot.indexing.providers.sqlite_fts import index_file_chunk
from ai_workroot.runtime.context import ContextRequest, build_context_package
from ai_workroot.runtime.init import initialize_workroot
from ai_workroot.runtime.work import create_checkpoint, create_handoff, create_task


def _parse_token_usage(output: str) -> int:
    for line in output.splitlines():
        if line.startswith("TokenUsage:"):
            usage = line.split(":", 1)[1].strip().split("/", 1)[0]
            return int(usage)
    raise AssertionError("missing TokenUsage line")


class IndexingContextControlTest(unittest.TestCase):
    def test_active_task_checkpoint_and_handoff_are_rendered_as_continuity_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, native_agent_entry=False, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                create_task(
                    conn,
                    workroot_id=workroot_id,
                    task_id="task-active-context",
                    title="Active Context parity task",
                    task_kind="architecture",
                    process_level="L2",
                )
                create_checkpoint(
                    conn,
                    workroot_id=workroot_id,
                    checkpoint_id="checkpoint-active-context",
                    task_id="task-active-context",
                    current_status="Checkpoint says release filters are green.",
                )
                create_handoff(
                    conn,
                    workroot_id=workroot_id,
                    handoff_id="handoff-active-context",
                    title="Next: verify Context Control parity.",
                )

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="parity", debug=True),
                ai_workroot_home=home,
            )

            self.assertIn("## Workroot", package)
            self.assertIn("Demo", package)
            self.assertIn("## Current Task", package)
            self.assertIn("Active Context parity task", package)
            self.assertIn("architecture", package)
            self.assertIn("L2", package)
            self.assertIn("## Continuity", package)
            self.assertIn("Checkpoint says release filters are green.", package)
            self.assertIn("Next: verify Context Control parity.", package)
            self.assertIn("continuitySources:", package)
            with sqlite3.connect(db_path) as conn:
                trace_json = conn.execute("SELECT debug_json FROM context_traces ORDER BY rowid DESC LIMIT 1").fetchone()[0]
            trace = json.loads(trace_json)
            self.assertEqual(trace["continuity"]["activeTaskId"], "task-active-context")
            self.assertEqual(trace["continuity"]["checkpointId"], "checkpoint-active-context")
            self.assertEqual(trace["continuity"]["handoffId"], "handoff-active-context")

    def test_context_modes_use_distinct_local_retrieval_budgets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, native_agent_entry=False, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                for index in range(12):
                    upsert_context_candidate(
                        conn,
                        {
                            "candidate_id": f"cand-mode-{index:02d}",
                            "workroot_id": workroot_id,
                            "source_type": "asset",
                            "source_id": f"asset-mode-{index:02d}",
                            "title": f"Mode candidate {index:02d}",
                            "summary": "Mode parity retrieval budget candidate.",
                            "importance": "high" if index < 6 else "normal",
                            "context_policy": "always",
                        },
                    )
                for index in range(6):
                    upsert_context_recall_hint(
                        conn,
                        ContextRecallHint(
                            hint_id=f"hint-mode-{index:02d}",
                            workroot_id=workroot_id,
                            target_type="asset",
                            target_id=f"asset-hint-{index:02d}",
                            title=f"Mode hint {index:02d}",
                            summary="Mode parity recall hint.",
                            priority="high",
                            recall_rule="always",
                        ),
                    )

            fast = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="", mode="fast", debug=True),
                ai_workroot_home=home,
            )
            standard = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="", mode="standard", debug=True),
                ai_workroot_home=home,
            )
            quality = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="", mode="quality", debug=True),
                ai_workroot_home=home,
            )

            self.assertIn("modePlan: mode=fast", fast)
            self.assertIn("modePlan: mode=standard", standard)
            self.assertIn("modePlan: mode=quality", quality)
            self.assertIn("quality-budget-expansion", quality)
            self.assertLessEqual(fast.count("Mode candidate"), standard.count("Mode candidate"))
            self.assertLessEqual(standard.count("Mode candidate"), quality.count("Mode candidate"))
            with sqlite3.connect(db_path) as conn:
                trace_payloads = [
                    json.loads(row[0])
                    for row in conn.execute("SELECT debug_json FROM context_traces ORDER BY rowid ASC").fetchall()
                ]
            self.assertEqual(trace_payloads[0]["modePlan"]["candidateLimit"], 4)
            self.assertEqual(trace_payloads[1]["modePlan"]["candidateLimit"], 8)
            self.assertEqual(trace_payloads[2]["modePlan"]["candidateLimit"], 12)
            self.assertEqual(trace_payloads[2]["modePlan"]["behavior"], "quality-budget-expansion")

    def test_deep_mode_records_explicit_local_retrieval_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, native_agent_entry=False, ai_workroot_home=home)
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="", mode="deep", debug=True),
                ai_workroot_home=home,
            )

            self.assertIn("modePlan: mode=deep", package)
            self.assertIn("deepExplicitlyRequested=true", package)
            with sqlite3.connect(db_path) as conn:
                trace = json.loads(conn.execute("SELECT debug_json FROM context_traces ORDER BY rowid DESC LIMIT 1").fetchone()[0])
            self.assertTrue(trace["modePlan"]["deepExplicitlyRequested"])

    def test_fallback_is_disabled_after_protected_release_drop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            (user_dir / "redacted-payroll-secret.md").write_text("fallback should not expose this filename\n", encoding="utf-8")
            init = initialize_workroot(name="Demo", directory=user_dir, native_agent_entry=False, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-protected-only",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-protected-only",
                        "title": "Redacted payroll secret",
                        "summary": "Protected candidate should be dropped.",
                        "importance": "critical",
                        "context_policy": "always",
                    },
                )
                conn.execute(
                    """
                    INSERT INTO release_records (release_id, workroot_id, target_type, target_id, release_level, recall_rule)
                    VALUES ('rel-protected-only', ?, 'asset', 'asset-protected-only', 'redacted', 'ordinary-context-excluded')
                    """,
                    (workroot_id,),
                )
                conn.commit()

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="payroll", debug=True),
                ai_workroot_home=home,
            )

            self.assertNotIn("redacted-payroll-secret.md", package)
            self.assertIn("- No context candidates selected.", package)
            self.assertIn("fallbackUserAssetCandidates: attempted=false reason=disabled_due_to_release_protected_drop", package)
            with sqlite3.connect(db_path) as conn:
                trace_json = conn.execute("SELECT debug_json FROM context_traces ORDER BY rowid DESC LIMIT 1").fetchone()[0]
            trace = json.loads(trace_json)
            self.assertEqual(
                trace["fallbackUserAssetCandidates"],
                {"attempted": False, "reason": "disabled_due_to_release_protected_drop"},
            )

    def test_query_fts_and_relationships_influence_selected_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            init = initialize_workroot(name="Demo", directory=user_dir, native_agent_entry=False, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-always",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-always",
                        "title": "General notes",
                        "summary": "Always visible but unrelated.",
                        "importance": "critical",
                        "context_policy": "always",
                    },
                )
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-clean",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-clean",
                        "title": "Clean Mode Design",
                        "summary": "Managed state stays outside user directories.",
                        "importance": "normal",
                    },
                )
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-blocked",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-blocked",
                        "title": "Sensitive blocked note",
                        "summary": "This should not enter ordinary context.",
                        "importance": "critical",
                        "safety_policy": "sensitive",
                    },
                )
                index_file_chunk(
                    conn,
                    workroot_id=workroot_id,
                    file_id="file-clean",
                    chunk_id="chunk-clean",
                    relative_path="design.md",
                    body="Clean Mode keeps managed state outside user directories.",
                )
                upsert_relationship_node(conn, "node-task", workroot_id, "task", "Clean Mode task")
                upsert_relationship_node(conn, "asset-clean", workroot_id, "asset", "Clean Mode Design")
                upsert_relationship_node(conn, "asset-weak", workroot_id, "asset", "Weak query-only node")
                upsert_relationship_edge(
                    conn,
                    edge_id="edge-clean",
                    workroot_id=workroot_id,
                    from_node_id="node-task",
                    to_node_id="asset-clean",
                    relationship_type="supports",
                    confidence=0.9,
                )

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="Clean Mode", debug=True, hard_token_limit=900),
                ai_workroot_home=home,
            )

            self.assertIn("Clean Mode Design", package)
            self.assertIn("candidate-fts-match", package)
            self.assertIn("file-fts-match", package)
            self.assertIn("Relationship Signals", package)
            self.assertIn("edge-clean", package)
            self.assertNotIn("Weak query-only node", package)
            self.assertNotIn("Sensitive blocked note", package)
            self.assertIn("candidateSources", package)
            self.assertIn("tokenUsage", package)
            self.assertIn("hard=900", package)

    def test_hard_token_limit_uses_final_fallback_and_records_trim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, native_agent_entry=False, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-long",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-long",
                        "title": "Long candidate",
                        "summary": "Clean Mode " * 300,
                        "importance": "critical",
                    },
                )

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="Clean Mode", debug=True, hard_token_limit=80, target_tokens=40),
                ai_workroot_home=home,
            )

            self.assertIn("trimSteps", package)
            self.assertIn("final-fallback", package)
            self.assertLessEqual(len(package), 80 * 6)

    def test_context_runtime_persists_package_trace_selection_and_trim_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, native_agent_entry=False, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-persist",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-persist",
                        "title": "Persisted context candidate",
                        "summary": "Persistence " * 200,
                        "importance": "critical",
                    },
                )

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="Persistence", debug=True, hard_token_limit=80, target_tokens=40),
                ai_workroot_home=home,
            )

            with sqlite3.connect(db_path) as conn:
                package_rows = conn.execute("SELECT mode, rendered FROM context_packages").fetchall()
                trace_rows = conn.execute("SELECT debug_json FROM context_traces").fetchall()
                selection_rows = conn.execute("SELECT candidate_id, reason FROM candidate_selections").fetchall()
                trim_rows = conn.execute("SELECT section, reason FROM budget_trim_decisions").fetchall()
                use_count = conn.execute(
                    "SELECT use_count FROM context_candidates WHERE candidate_id = 'cand-persist'"
                ).fetchone()[0]

            self.assertIn("TokenUsage:", package)
            self.assertEqual(len(package_rows), 1)
            self.assertEqual(package_rows[0][0], "standard")
            self.assertIn("# AI Workroot Context Package", package_rows[0][1])
            self.assertEqual(len(trace_rows), 1)
            self.assertIn("final-fallback", trace_rows[0][0])
            self.assertIn(("cand-persist", "selected"), selection_rows)
            self.assertIn(("rendered-package", "final-fallback"), trim_rows)
            self.assertEqual(use_count, 1)

    def test_final_rendered_package_respects_hard_token_limit_after_trim_marker(self) -> None:
        from ai_workroot.runtime.context import estimate_tokens

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, native_agent_entry=False, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-long-marker",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-long-marker",
                        "title": "Long marker candidate",
                        "summary": "没有空格的中文内容" * 200,
                        "importance": "critical",
                    },
                )

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="中文", debug=True, hard_token_limit=60, target_tokens=30),
                ai_workroot_home=home,
            )

            self.assertLessEqual(estimate_tokens(package), 60)

    def test_debug_trace_survives_hard_token_trim(self) -> None:
        from ai_workroot.runtime.context import estimate_tokens

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, native_agent_entry=False, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-debug-trim",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-debug-trim",
                        "title": "Large context debug trim",
                        "summary": "large context trim budget " * 300,
                        "importance": "critical",
                    },
                )

            package = build_context_package(
                ContextRequest(
                    agent="codex",
                    cwd=user_dir,
                    query="large context trim budget",
                    debug=True,
                    hard_token_limit=180,
                    target_tokens=120,
                ),
                ai_workroot_home=home,
            )

            self.assertLessEqual(estimate_tokens(package), 180)
            self.assertIn("## Debug Trace", package)
            self.assertIn("candidateSources:", package)
            self.assertIn("scoring:", package)
            self.assertIn("timing:", package)
            self.assertIn("tokenUsage:", package)
            self.assertIn("trimSteps:", package)
            reported = _parse_token_usage(package)
            self.assertGreaterEqual(reported, estimate_tokens(package))

    def test_context_recall_hint_affects_active_context_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, native_agent_entry=False, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                upsert_context_recall_hint(
                    conn,
                    ContextRecallHint(
                        hint_id="hint-context-card",
                        workroot_id=workroot_id,
                        target_type="task",
                        target_id="task-context-card",
                        title="Context Card parity anchor",
                        summary="Recall this Context Card when parity is discussed.",
                        priority="critical",
                        recall_rule="always",
                    ),
                )

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="parity", debug=True),
                ai_workroot_home=home,
            )

            self.assertIn("Context Card parity anchor", package)
            self.assertIn("context_recall_hint", package)
            self.assertIn("candidate-fts-match", package)
            with sqlite3.connect(db_path) as conn:
                selection = conn.execute(
                    """
                    SELECT candidate_id, reason
                    FROM candidate_selections
                    WHERE candidate_id = 'hint:hint-context-card'
                    """
                ).fetchone()
                use_count = conn.execute(
                    """
                    SELECT use_count
                    FROM context_candidates
                    WHERE candidate_id = 'hint:hint-context-card'
                    """
                ).fetchone()[0]

            self.assertEqual(selection, ("hint:hint-context-card", "selected"))
            self.assertEqual(use_count, 1)

    def test_redacted_context_recall_hint_target_is_excluded_from_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, native_agent_entry=False, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                upsert_context_recall_hint(
                    conn,
                    ContextRecallHint(
                        hint_id="hint-redacted-target",
                        workroot_id=workroot_id,
                        target_type="task",
                        target_id="task-redacted",
                        title="Redacted target hint",
                        summary="This should be blocked through its target release state.",
                        priority="critical",
                        recall_rule="always",
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO redactions (
                      redaction_id, workroot_id, target_type, target_id, redacted_fields, redaction_reason
                    )
                    VALUES ('redact-task', ?, 'task', 'task-redacted', 'summary', 'test')
                    """,
                    (workroot_id,),
                )

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="target", debug=True),
                ai_workroot_home=home,
            )

            self.assertNotIn("Redacted target hint", package)
            self.assertIn("releaseFilters: dropped=hint:hint-redacted-target:redacted", package)

    def test_tombstone_context_recall_hint_target_is_annotated_not_hard_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, native_agent_entry=False, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                upsert_context_recall_hint(
                    conn,
                    ContextRecallHint(
                        hint_id="hint-tombstone-target",
                        workroot_id=workroot_id,
                        target_type="task",
                        target_id="task-tombstone",
                        title="Tombstone target hint",
                        summary="This should stay recallable with tombstone annotation.",
                        priority="critical",
                        recall_rule="always",
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO tombstones (
                      tombstone_id, workroot_id, target_type, target_id, title, symbolic_note
                    )
                    VALUES ('tomb-task', ?, 'task', 'task-tombstone', 'Old task', 'kept as tombstone')
                    """,
                    (workroot_id,),
                )

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="tombstone", debug=True),
                ai_workroot_home=home,
            )

            self.assertIn("Tombstone target hint", package)
            self.assertIn("annotated-release-state", package)
            self.assertIn("releaseFilters: dropped=none annotated=hint-tombstone-target", package)


if __name__ == "__main__":
    unittest.main()
