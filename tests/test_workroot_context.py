from __future__ import annotations

import os
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.workroot_candidates import ContextCandidate, upsert_context_candidate
from scripts.workroot_context import ContextRequest, build_context_package
from scripts.workroot_indexing import index_text_file
from scripts.workroot_paths import workroot_sqlite_path
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
        db_path = workroot_sqlite_path(initialized.state_directory)
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
        self.assertIn("## Context Metadata", package.markdown)
        self.assertIn("Mode: standard", package.markdown)
        self.assertIn("Confidence: high", package.markdown)
        self.assertIn("Tokens:", package.markdown)
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

    def test_fts_match_promotes_related_context_candidate(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_query_match",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="knowledge-query",
                    title="Query specific retrieval",
                    summary="This summary is found only through context candidate FTS.",
                    domains="rare-domain",
                    importance="low",
                    confidence=0.8,
                    context_policy="on-demand",
                    token_estimate=6,
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )

        package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="rare-domain",
                now="2026-05-19T00:00:00Z",
            )
        )

        selected = {item["candidateId"]: item for item in package.trace["selectedCandidates"]}
        self.assertIn("cand_query_match", selected)
        self.assertIn("candidate-fts-match", selected["cand_query_match"]["reasons"])

    def test_graph_signals_are_related_to_selected_candidates(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            conn.execute(
                """
                INSERT INTO graph_nodes (
                  node_id, node_type, kind, title, summary, status, importance, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "unrelated-critical",
                    "decision",
                    "architecture",
                    "Unrelated critical node",
                    "This high priority node is unrelated and should not appear.",
                    "active",
                    "critical",
                    "2026-05-19T00:00:00Z",
                    "2026-05-19T00:00:00Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO graph_edges (
                  edge_id, from_node_id, to_node_id, relation, strength, confidence, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "edge-clean-task",
                    "decision-1",
                    "task-1",
                    "belongs_to_task",
                    1.0,
                    0.9,
                    "active",
                    "2026-05-19T00:00:00Z",
                    "2026-05-19T00:00:00Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO graph_nodes (
                  node_id, node_type, kind, title, summary, status, importance, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "task-1",
                    "task",
                    "work",
                    "Clean Mode task",
                    "Task linked by one-hop graph edge.",
                    "active",
                    "normal",
                    "2026-05-19T00:00:00Z",
                    "2026-05-19T00:00:00Z",
                ),
            )
            conn.commit()

        package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="clean mode",
                now="2026-05-19T00:00:00Z",
            )
        )

        titles = {signal["title"] for signal in package.trace["graphSignals"]}
        self.assertIn("Clean Mode task", titles)
        self.assertNotIn("Unrelated critical node", titles)

    def test_graph_signals_do_not_use_broad_focus_terms_for_unrelated_nodes(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        write_json(
            state_dir / "state/current.json",
            {
                "currentFocus": "Clean Mode local Context Guide review.",
                "activeTaskId": "task-1",
                "nextSuggestedAction": "Review context output.",
                "contextVersion": 1,
                "lastActivityAt": "2026-05-19T00:00:00Z",
            },
        )
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            conn.execute(
                """
                INSERT INTO graph_nodes (
                  node_id, node_type, kind, title, summary, status, importance, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "unrelated-critical",
                    "decision",
                    "architecture",
                    "Unrelated critical context node",
                    "This unrelated node contains context and should not appear without a related edge.",
                    "active",
                    "critical",
                    "2026-05-19T00:00:00Z",
                    "2026-05-19T00:00:00Z",
                ),
            )
            conn.commit()

        package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                now="2026-05-19T00:00:00Z",
            )
        )

        titles = {signal["title"] for signal in package.trace["graphSignals"]}
        self.assertNotIn("Unrelated critical context node", titles)

    def test_graph_one_hop_match_promotes_candidate_selection(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        hints = json.loads((state_dir / "state/runtime-hints.json").read_text(encoding="utf-8"))
        hints["contextGuide"]["agentBudgets"]["codex"]["targetTokens"] = 5
        (state_dir / "state/runtime-hints.json").write_text(json.dumps(hints, ensure_ascii=False, indent=2), encoding="utf-8")
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_unrelated",
                    workroot_id="wr_demo",
                    source_type="knowledge",
                    source_id="knowledge-unrelated",
                    title="Unrelated normal context",
                    summary="This candidate has a stronger base score but no graph relation.",
                    importance="normal",
                    confidence=0.8,
                    context_policy="task-related",
                    token_estimate=5,
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_graph_task",
                    workroot_id="wr_demo",
                    source_type="decision",
                    source_id="decision-task-related",
                    title="Task graph context",
                    summary="This candidate is related through a one-hop active task graph edge.",
                    importance="low",
                    confidence=0.8,
                    context_policy="on-demand",
                    token_estimate=5,
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO graph_nodes (
                  node_id, node_type, kind, title, summary, status, importance, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "decision-task-related",
                    "decision",
                    "architecture",
                    "Task related graph node",
                    "Graph node connected to the active task.",
                    "active",
                    "low",
                    "2026-05-19T00:00:00Z",
                    "2026-05-19T00:00:00Z",
                ),
            )
            conn.execute(
                """
                INSERT INTO graph_edges (
                  edge_id, from_node_id, to_node_id, relation, strength, confidence, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "edge-task-related-decision",
                    "decision-task-related",
                    "task-1",
                    "belongs_to_task",
                    1.0,
                    0.9,
                    "active",
                    "2026-05-19T00:00:00Z",
                    "2026-05-19T00:00:00Z",
                ),
            )
            conn.commit()

        package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="",
                mode="fast",
                target_token_budget=5,
                now="2026-05-19T00:00:00Z",
            )
        )

        selected = {item["candidateId"]: item for item in package.trace["selectedCandidates"]}
        self.assertIn("cand_graph_task", selected)
        self.assertIn("graph-one-hop-match", selected["cand_graph_task"]["reasons"])
        self.assertNotIn("cand_unrelated", selected)

    def test_token_usage_estimates_full_context_package(self) -> None:
        home, user_dir, _ = self.create_fixture()

        package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="clean mode",
                now="2026-05-19T00:00:00Z",
            )
        )

        estimated = package.trace["tokenBudget"]["estimatedUsed"]
        self.assertGreater(estimated, sum(item["tokenEstimate"] for item in package.trace["selectedCandidates"]))
        self.assertNotIn("Tokens: 0", package.markdown)

    def test_context_uses_agent_specific_token_budgets(self) -> None:
        home, user_dir, _ = self.create_fixture()

        codex_package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="clean mode",
                now="2026-05-19T00:00:00Z",
            )
        )
        claude_package = build_context_package(
            ContextRequest(
                home=home,
                agent="claude",
                cwd=user_dir,
                query="clean mode",
                now="2026-05-19T00:00:00Z",
            )
        )

        self.assertEqual(codex_package.trace["tokenBudget"]["source"], "agent:codex")
        self.assertEqual(codex_package.trace["tokenBudget"]["hard"], 6000)
        self.assertEqual(claude_package.trace["tokenBudget"]["source"], "agent:claude")
        self.assertEqual(claude_package.trace["tokenBudget"]["hard"], 8000)
        self.assertIn("Tokens:", codex_package.markdown)

    def test_standard_to_quality_escalation_reselects_with_quality_budget(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        hints = json.loads((state_dir / "state/runtime-hints.json").read_text(encoding="utf-8"))
        hints["contextGuide"]["agentBudgets"]["codex"]["targetTokens"] = 5
        hints["contextGuide"]["modes"]["quality"]["targetTokens"] = 50
        (state_dir / "state/runtime-hints.json").write_text(json.dumps(hints, ensure_ascii=False, indent=2), encoding="utf-8")
        write_json(
            state_dir / "state/current.json",
            {
                "currentFocus": "clean mode",
                "activeTaskId": None,
                "nextSuggestedAction": "",
                "contextVersion": 1,
                "lastActivityAt": "2026-05-19T00:00:00Z",
            },
        )
        db_path = workroot_sqlite_path(state_dir)
        with open_sqlite(db_path) as conn:
            upsert_context_candidate(
                conn,
                ContextCandidate(
                    candidate_id="cand_quality_extra",
                    workroot_id="wr_demo",
                    source_type="decision",
                    source_id="decision-quality",
                    title="Quality extra context",
                    summary="Quality mode should include this candidate after escalation.",
                    importance="high",
                    confidence=0.9,
                    context_policy="always",
                    token_estimate=4,
                    updated_at="2026-05-19T00:00:00Z",
                ),
            )

        package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="clean mode",
                debug=True,
                now="2026-05-19T00:00:00Z",
            )
        )

        self.assertEqual(package.trace["contextMode"], "quality")
        self.assertEqual(package.trace["qualityBehavior"], "quality-budget-expansion")
        selected_ids = {item["candidateId"] for item in package.trace["selectedCandidates"]}
        dropped = {item["candidateId"]: item["reason"] for item in package.trace["droppedCandidates"]}
        self.assertIn("cand_quality_extra", selected_ids)
        self.assertNotEqual(dropped.get("cand_quality_extra"), "token-budget")
        self.assertEqual(package.trace["tokenBudget"]["target"], 50)

    def test_malformed_runtime_hint_numeric_values_fall_back_safely(self) -> None:
        home, user_dir, state_dir = self.create_fixture()
        hints = json.loads((state_dir / "state/runtime-hints.json").read_text(encoding="utf-8"))
        hints["contextGuide"]["agentBudgets"]["codex"]["targetTokens"] = "abc"
        (state_dir / "state/runtime-hints.json").write_text(json.dumps(hints, ensure_ascii=False, indent=2), encoding="utf-8")

        package = build_context_package(
            ContextRequest(
                home=home,
                agent="codex",
                cwd=user_dir,
                query="clean mode",
                now="2026-05-19T00:00:00Z",
            )
        )

        self.assertIn("runtime-hints-invalid-budget", package.trace["fallbacks"])
        self.assertEqual(package.trace["tokenBudget"]["hard"], 6000)

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

    def test_cli_context_supports_quality_mode_and_debug_trace(self) -> None:
        home, user_dir, state_dir = self.create_fixture()

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
                "--mode",
                "quality",
                "--debug",
            ],
            cwd=ROOT,
            env={**os.environ, "AI_WORKROOT_HOME": str(home)},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Mode: quality", result.stdout)
        trace = json.loads((state_dir / "context/debug/latest.json").read_text(encoding="utf-8"))
        self.assertEqual(trace["requestedMode"], "quality")
        self.assertEqual(trace["contextMode"], "quality")
        self.assertEqual(trace["tokenBudget"]["hard"], 12000)

    def test_cli_context_deep_requires_explicit_request_and_records_it(self) -> None:
        home, user_dir, state_dir = self.create_fixture()

        result = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "context",
                "--agent",
                "codex",
                "--cwd",
                str(user_dir),
                "--deep",
                "--debug",
            ],
            cwd=ROOT,
            env={**os.environ, "AI_WORKROOT_HOME": str(home)},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Mode: deep", result.stdout)
        trace = json.loads((state_dir / "context/debug/latest.json").read_text(encoding="utf-8"))
        self.assertTrue(trace["deepExplicitlyRequested"])
        self.assertEqual(trace["contextMode"], "deep")

    def test_cli_context_rejects_target_tokens_over_hard_limit(self) -> None:
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
                "--target-tokens",
                "999999",
            ],
            cwd=ROOT,
            env={**os.environ, "AI_WORKROOT_HOME": str(home)},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exceeds hard token limit", result.stderr)

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
