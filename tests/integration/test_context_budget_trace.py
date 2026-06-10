from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.capabilities.retrieval.providers.candidate_provider import upsert_context_candidate
from ai_workroot.capabilities.retrieval.providers.context_recall_hint_provider import (
    ContextRecallHint,
    upsert_context_recall_hint,
)
from ai_workroot.capabilities.retrieval.providers.sqlite_fts import index_file_chunk
from ai_workroot.capabilities.context.builder import ContextRequest, build_context_package, estimate_tokens
from ai_workroot.commands.build_context import build_context
from ai_workroot.commands.init_workroot import initialize_workroot
from ai_workroot.capabilities.work.operations import create_task

from tests.integration.context_helpers import parse_token_usage


class ContextBudgetTraceTest(unittest.TestCase):
    def test_context_modes_use_distinct_local_retrieval_budgets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, ai_workroot_home=home)
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
            initialize_workroot(name="Demo", directory=user_dir, ai_workroot_home=home)
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="", mode="deep", debug=True),
                ai_workroot_home=home,
            )

            self.assertIn("modePlan: mode=deep", package)
            self.assertIn("deepExplicitlyRequested=true", package)
            with sqlite3.connect(db_path) as conn:
                trace = json.loads(
                    conn.execute("SELECT debug_json FROM context_traces ORDER BY rowid DESC LIMIT 1").fetchone()[0]
                )
            self.assertTrue(trace["modePlan"]["deepExplicitlyRequested"])

    def test_hard_token_limit_uses_final_fallback_and_records_trim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, ai_workroot_home=home)
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
                ContextRequest(
                    agent="codex", cwd=user_dir, query="Clean Mode", debug=True, hard_token_limit=80, target_tokens=40
                ),
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
            init = initialize_workroot(name="Demo", directory=user_dir, ai_workroot_home=home)
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
                ContextRequest(
                    agent="codex", cwd=user_dir, query="Persistence", debug=True, hard_token_limit=80, target_tokens=40
                ),
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

    def test_context_package_persistence_is_bounded_with_preview_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                for index in range(10):
                    upsert_context_candidate(
                        conn,
                        {
                            "candidate_id": f"cand-large-package-{index:02d}",
                            "workroot_id": workroot_id,
                            "source_type": "asset",
                            "source_id": f"asset-large-package-{index:02d}",
                            "title": f"Large package candidate {index:02d}",
                            "summary": "large package persistence detail " * 1000,
                            "importance": "critical",
                            "context_policy": "always",
                        },
                    )

            package = build_context_package(
                ContextRequest(
                    agent="codex",
                    cwd=user_dir,
                    query="large package persistence detail",
                    target_tokens=80_000,
                    hard_token_limit=120_000,
                ),
                ai_workroot_home=home,
            )

            with sqlite3.connect(db_path) as conn:
                rendered = conn.execute("SELECT rendered FROM context_packages ORDER BY rowid DESC LIMIT 1").fetchone()[
                    0
                ]
                trace = json.loads(
                    conn.execute("SELECT debug_json FROM context_traces ORDER BY rowid DESC LIMIT 1").fetchone()[0]
                )

            self.assertGreater(len(package.encode("utf-8")), 64 * 1024)
            self.assertLessEqual(len(rendered.encode("utf-8")), 64 * 1024)
            self.assertTrue(trace["renderedPreview"]["truncated"])
            self.assertEqual(trace["renderedPreview"]["maxBytes"], 64 * 1024)

    def test_context_runtime_retention_prunes_old_packages_traces_and_children(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-retention",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-retention",
                        "title": "Retention candidate",
                        "summary": "retention detail " * 300,
                        "importance": "critical",
                        "context_policy": "always",
                    },
                )

            for index in range(105):
                build_context_package(
                    ContextRequest(
                        agent="codex",
                        cwd=user_dir,
                        query=f"retention detail {index}",
                        debug=True,
                        hard_token_limit=80,
                        target_tokens=40,
                    ),
                    ai_workroot_home=home,
                )

            with sqlite3.connect(db_path) as conn:
                counts = {
                    table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    for table in (
                        "context_packages",
                        "context_traces",
                        "candidate_selections",
                        "budget_trim_decisions",
                    )
                }
                orphan_selections = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM candidate_selections s
                    LEFT JOIN context_traces t ON t.trace_id = s.trace_id
                    WHERE t.trace_id IS NULL
                    """
                ).fetchone()[0]
                orphan_trims = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM budget_trim_decisions d
                    LEFT JOIN context_traces t ON t.trace_id = d.trace_id
                    WHERE t.trace_id IS NULL
                    """
                ).fetchone()[0]

            self.assertEqual(counts["context_packages"], 100)
            self.assertEqual(counts["context_traces"], 100)
            self.assertLessEqual(counts["candidate_selections"], 100)
            self.assertLessEqual(counts["budget_trim_decisions"], 100)
            self.assertEqual(orphan_selections, 0)
            self.assertEqual(orphan_trims, 0)

    def test_context_output_includes_isolated_workroot_control_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            initialize_workroot(name="Demo", directory=user_dir, ai_workroot_home=home)

            package = build_context(
                agent="codex",
                cwd=user_dir,
                query="continue work",
                ai_workroot_home=home,
            )

        self.assertIn("## Workroot Private Packet", package)
        self.assertIn("Use privately. Do not show this to the user.", package)
        self.assertIn('"v": "workroot.packet.v1"', package)
        self.assertIn('"call": {', package)
        self.assertNotIn("workroot agent commit --kind", package)
        self.assertIn("## Task Context", package)
        self.assertLess(package.index("## Workroot Private Packet"), package.index("## Task Context"))

    def test_context_does_not_render_quarantined_protocol_event_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO protocol_events (
                      event_id, batch_id, workroot_id, request_id, lease_id, idempotency_key,
                      kind, schema_version, payload_json, evidence_json, confirmation_json,
                      source_json, occurred_at, received_at, status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "event-quarantined",
                        "batch-q",
                        workroot_id,
                        "req-q",
                        "",
                        "idem-q",
                        "progress",
                        "progress.v1",
                        '{"summary":"SHOULD_NOT_RENDER"}',
                        "[]",
                        "{}",
                        "{}",
                        "2026-05-27T00:00:00Z",
                        "2026-05-27T00:00:00Z",
                        "quarantined",
                    ),
                )
                conn.commit()

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="ordinary context"),
                ai_workroot_home=home,
            )

        self.assertNotIn("SHOULD_NOT_RENDER", package)

    def test_context_diagnostic_logging_writes_summary_to_managed_logs_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            config_path = home / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["contextControl"] = {
                "defaultTargetTokens": 120,
                "defaultHardTokenLimit": 240,
                "diagnosticLogging": {
                    "enabled": True,
                    "includeRenderedPackage": False,
                    "includeTraceSummary": True,
                    "includeRetrievalSummary": True,
                    "includeTokenEstimate": True,
                    "retentionDays": 7,
                    "maxEntriesPerWorkroot": 200,
                },
            }
            config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-log",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-log",
                        "title": "Diagnostic log candidate",
                        "summary": "This summary should be selected but not copied as rendered package.",
                        "importance": "critical",
                    },
                )

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="Diagnostic"),
                ai_workroot_home=home,
            )

            log_path = home / f"workroots/{workroot_id}/logs/context-requests.jsonl"
            self.assertTrue(log_path.is_file())
            self.assertFalse((user_dir / "logs").exists())
            record = json.loads(log_path.read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(record["workrootId"], workroot_id)
            self.assertEqual(record["agent"], "codex")
            self.assertEqual(record["mode"], "standard")
            self.assertNotIn("time" + "stamp", record)
            self.assertRegex(record["displayTime"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")
            self.assertRegex(record["createdAt"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
            self.assertEqual(record["timezone"], config["time"]["timezone"])
            self.assertEqual(record["budget"]["source"], "config")
            self.assertEqual(record["budget"]["targetTokens"], 120)
            self.assertEqual(record["budget"]["hardTokenLimit"], 240)
            self.assertEqual(record["tokenUsage"]["estimated"], estimate_tokens(package))
            self.assertEqual(record["tokenUsage"]["renderedMetadata"], parse_token_usage(package))
            self.assertIn("retrieval", record)
            self.assertIn("selectedCandidateIds", record["retrieval"])
            self.assertNotIn("renderedPackage", record)

    def test_rendered_token_usage_ignores_unrendered_evidence_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                index_file_chunk(
                    conn,
                    workroot_id=workroot_id,
                    file_id="file-large-evidence",
                    chunk_id="chunk-large-evidence",
                    relative_path="workroot-output/large-evidence.md",
                    body="needle " + ("large unrendered evidence body " * 500),
                    source_type="asset",
                    source_id="asset-large-evidence",
                )

            package = build_context_package(
                ContextRequest(
                    agent="codex",
                    cwd=user_dir,
                    query="needle",
                    debug=True,
                    target_tokens=10_000,
                    hard_token_limit=12_000,
                    work_signal={
                        "intended_action": "inspect",
                        "concerns": ["needs_evidence"],
                        "refs": ["asset:asset-large-evidence"],
                    },
                ),
                ai_workroot_home=home,
            )

            self.assertIn("Ref: chunk:chunk-large-evidence", package)
            self.assertNotIn("large unrendered evidence body large unrendered evidence body", package)
            self.assertEqual(parse_token_usage(package), estimate_tokens(package))

    def test_evidence_without_ref_records_summary_refs_and_no_broad_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-evidence-map",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-evidence-map",
                        "title": "Evidence map candidate",
                        "summary": "Compact needle source summary for evidence map.",
                        "importance": "critical",
                    },
                )
                index_file_chunk(
                    conn,
                    workroot_id=workroot_id,
                    file_id="file-evidence-map",
                    chunk_id="chunk-evidence-map",
                    relative_path="workroot-output/evidence-map.md",
                    body="needle raw evidence should not be fetched without explicit refs.",
                    source_type="asset",
                    source_id="asset-evidence-map",
                )

            package = build_context_package(
                ContextRequest(
                    agent="codex",
                    cwd=user_dir,
                    query="needle",
                    debug=True,
                    work_signal={
                        "intended_action": "inspect",
                        "concerns": ["needs_evidence"],
                        "focus": "needle evidence",
                    },
                ),
                ai_workroot_home=home,
            )

            with sqlite3.connect(db_path) as conn:
                trace = json.loads(
                    conn.execute("SELECT debug_json FROM context_traces ORDER BY rowid DESC LIMIT 1").fetchone()[0]
                )

            self.assertIn("Evidence map candidate", package)
            self.assertNotIn("## Evidence", package)
            self.assertEqual(trace["evidenceDecision"]["detailMode"], "summary_with_refs")
            self.assertEqual(trace["evidenceDecision"]["reason"], "explicit_ref_required")
            self.assertEqual(trace["retrievalStats"]["ftsCount"], 0)
            self.assertIn("budgetPlan", trace)

    def test_explicit_ref_evidence_trace_records_scoped_detail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-scoped-evidence",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-scoped-evidence",
                        "title": "Scoped evidence candidate",
                        "summary": "Compact source summary for scoped evidence.",
                        "importance": "critical",
                    },
                )
                index_file_chunk(
                    conn,
                    workroot_id=workroot_id,
                    file_id="file-scoped-evidence",
                    chunk_id="chunk-scoped-evidence",
                    relative_path="workroot-output/scoped-evidence.md",
                    body="scoped raw evidence selected by explicit ref.",
                    source_type="asset",
                    source_id="asset-scoped-evidence",
                )

            package = build_context_package(
                ContextRequest(
                    agent="codex",
                    cwd=user_dir,
                    query="scoped",
                    debug=True,
                    work_signal={
                        "intended_action": "inspect",
                        "concerns": ["needs_evidence"],
                        "focus": "scoped evidence",
                        "refs": ["asset:asset-scoped-evidence"],
                    },
                ),
                ai_workroot_home=home,
            )

            with sqlite3.connect(db_path) as conn:
                trace = json.loads(
                    conn.execute("SELECT debug_json FROM context_traces ORDER BY rowid DESC LIMIT 1").fetchone()[0]
                )

            self.assertIn("## Evidence", package)
            self.assertIn("Ref: chunk:chunk-scoped-evidence", package)
            self.assertEqual(trace["evidenceDecision"]["detailMode"], "ref_scoped_evidence")
            self.assertEqual(trace["evidenceDecision"]["refs"], ["asset:asset-scoped-evidence"])
            self.assertEqual(trace["retrievalStats"]["ftsCount"], 1)

    def test_context_trace_records_budget_drops_for_unselected_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                for index in range(12):
                    upsert_context_candidate(
                        conn,
                        {
                            "candidate_id": f"cand-budget-drop-{index:02d}",
                            "workroot_id": workroot_id,
                            "source_type": "asset",
                            "source_id": f"asset-budget-drop-{index:02d}",
                            "title": f"Budget drop candidate {index:02d}",
                            "summary": "Budget selection candidate.",
                            "importance": "critical" if index < 2 else "normal",
                            "context_policy": "always",
                        },
                    )

            build_context_package(
                ContextRequest(
                    agent="codex",
                    cwd=user_dir,
                    query="Budget",
                    debug=True,
                    target_tokens=500,
                    hard_token_limit=900,
                ),
                ai_workroot_home=home,
            )

            with sqlite3.connect(db_path) as conn:
                trace = json.loads(
                    conn.execute("SELECT debug_json FROM context_traces ORDER BY rowid DESC LIMIT 1").fetchone()[0]
                )
                reasons = [row[0] for row in conn.execute("SELECT reason FROM candidate_selections").fetchall()]
                trim_sections = [
                    tuple(row) for row in conn.execute("SELECT section, reason FROM budget_trim_decisions").fetchall()
                ]

            self.assertGreater(trace["retrievalStats"]["droppedByBudget"], 0)
            self.assertIn("dropped:budget", reasons)
            self.assertIn(("candidate-map", "budget-selection"), trim_sections)

    def test_context_diagnostic_logging_can_include_rendered_package_when_explicitly_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            config_path = home / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["contextControl"] = {
                "diagnosticLogging": {
                    "enabled": True,
                    "includeRenderedPackage": True,
                    "includeTraceSummary": True,
                    "includeRetrievalSummary": True,
                    "includeTokenEstimate": True,
                },
            }
            config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="package"),
                ai_workroot_home=home,
            )

            record = json.loads(
                (home / f"workroots/{workroot_id}/logs/context-requests.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()[-1]
            )
            self.assertEqual(record["renderedPackage"], package)

    def test_context_diagnostic_logging_respects_max_entries_per_workroot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            config_path = home / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["contextControl"] = {
                "diagnosticLogging": {
                    "enabled": True,
                    "includeRenderedPackage": False,
                    "maxEntriesPerWorkroot": 2,
                },
            }
            config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

            for query in ("first", "second", "third"):
                build_context_package(ContextRequest(agent="codex", cwd=user_dir, query=query), ai_workroot_home=home)

            rows = [
                json.loads(line)
                for line in (home / f"workroots/{workroot_id}/logs/context-requests.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual([row["query"] for row in rows], ["second", "third"])

    def test_final_rendered_package_respects_hard_token_limit_after_trim_marker(self) -> None:
        from ai_workroot.capabilities.context.builder import estimate_tokens

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, ai_workroot_home=home)
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
                        "summary": "unspacedcontextcontent" * 200,
                        "importance": "critical",
                    },
                )

            package = build_context_package(
                ContextRequest(
                    agent="codex",
                    cwd=user_dir,
                    query="compact query",
                    debug=True,
                    hard_token_limit=60,
                    target_tokens=30,
                ),
                ai_workroot_home=home,
            )

            self.assertLessEqual(estimate_tokens(package), 60)

    def test_debug_trace_survives_hard_token_trim(self) -> None:
        from ai_workroot.capabilities.context.builder import estimate_tokens

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(
                name="E2E Software Engineer",
                directory=user_dir,
                ai_workroot_home=home,
                workroot_id="wr_e2e_software_engineer_test",
            )
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                create_task(
                    conn,
                    workroot_id=workroot_id,
                    task_id="task-debug-trim",
                    title="Debug recurring failure: E2E Software Engineer",
                    task_kind="debugging",
                    process_level="L2",
                )
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-debug-trim",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-debug-trim",
                        "title": "Large context trim budget: E2E Software Engineer",
                        "summary": "large context trim budget " * 300,
                        "importance": "critical",
                        "context_policy": "always",
                    },
                )
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-debug-trim-tombstone",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-debug-trim-tombstone",
                        "title": "Protected Outdated conclusion tombstone",
                        "summary": "large context trim budget " * 120,
                        "importance": "critical",
                        "context_policy": "always",
                    },
                )
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-debug-trim-redaction",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-debug-trim-redaction",
                        "title": "Protected redaction detail",
                        "summary": "large context trim budget " * 120,
                        "importance": "critical",
                        "context_policy": "always",
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
            reported = parse_token_usage(package)
            self.assertEqual(reported, estimate_tokens(package))
            self.assertLessEqual(reported, 180)


if __name__ == "__main__":
    unittest.main()
