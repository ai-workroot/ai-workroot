from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.indexing.providers.candidate_provider import upsert_context_candidate
from ai_workroot.indexing.providers.context_recall_hint_provider import ContextRecallHint, upsert_context_recall_hint
from ai_workroot.runtime.context import ContextRequest, build_context_package, estimate_tokens
from ai_workroot.runtime.init import initialize_workroot
from ai_workroot.runtime.work import create_task

from tests.integration.context_helpers import parse_token_usage


class ContextBudgetTraceTest(unittest.TestCase):
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
            initialize_workroot(name="Demo", directory=user_dir, native_agent_entry=False, ai_workroot_home=home)
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

    def test_context_diagnostic_logging_writes_summary_to_managed_logs_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, native_agent_entry=False, ai_workroot_home=home)
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
            self.assertEqual(record["budget"]["source"], "config")
            self.assertEqual(record["budget"]["targetTokens"], 120)
            self.assertEqual(record["budget"]["hardTokenLimit"], 240)
            self.assertEqual(record["tokenUsage"]["estimated"], estimate_tokens(package))
            self.assertIn("retrieval", record)
            self.assertIn("selectedCandidateIds", record["retrieval"])
            self.assertNotIn("renderedPackage", record)

    def test_context_diagnostic_logging_can_include_rendered_package_when_explicitly_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, native_agent_entry=False, ai_workroot_home=home)
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

            record = json.loads((home / f"workroots/{workroot_id}/logs/context-requests.jsonl").read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(record["renderedPackage"], package)

    def test_context_diagnostic_logging_respects_max_entries_per_workroot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, native_agent_entry=False, ai_workroot_home=home)
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
                for line in (home / f"workroots/{workroot_id}/logs/context-requests.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([row["query"] for row in rows], ["second", "third"])

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
            init = initialize_workroot(
                name="E2E Software Engineer",
                directory=user_dir,
                native_agent_entry=False,
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
