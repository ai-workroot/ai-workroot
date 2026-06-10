from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.commands.build_context import build_context
from ai_workroot.capabilities.context.control import workroot_guidance_text
from ai_workroot.protocol.lease import create_lease
from ai_workroot.state.environment import initialize_environment, register_workroot
from ai_workroot.state.layout import workroot_sqlite_path
from ai_workroot.state.sqlite import initialize_workroot_sqlite


class ContextWrapperV2Test(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / "ai-home"
        self.user_dir = Path(self.tmp.name) / "workspace"
        self.user_dir.mkdir()
        initialize_environment(self.home)
        self.registration = register_workroot(
            self.home,
            workroot_id="wr_demo",
            name="Demo",
            user_directory=self.user_dir,
        )
        self.sqlite_path = workroot_sqlite_path(Path(self.registration.state_directory))
        initialize_workroot_sqlite(self.sqlite_path)
        self.previous_home = os.environ.get("AI_WORKROOT_HOME")
        os.environ["AI_WORKROOT_HOME"] = str(self.home)
        self.addCleanup(self.restore_home)

    def restore_home(self) -> None:
        if self.previous_home is None:
            os.environ.pop("AI_WORKROOT_HOME", None)
        else:
            os.environ["AI_WORKROOT_HOME"] = self.previous_home

    def test_context_wrapper_does_not_mint_lease_or_create_work_facts(self) -> None:
        before = self.count_rows(
            "exchange_leases",
            "protocol_events",
            "protocol_commit_batches",
            "tasks",
            "task_runs",
            "task_summaries",
            "handoffs",
        )

        rendered = build_context(agent="codex", cwd=self.user_dir, query="Review protocol v2")

        after = self.count_rows(
            "exchange_leases",
            "protocol_events",
            "protocol_commit_batches",
            "tasks",
            "task_runs",
            "task_summaries",
            "handoffs",
        )
        self.assertEqual(after, before)
        self.assertIn("workroot agent sync", rendered)
        self.assertNotIn("Use sync to", rendered)
        self.assertIn("## Workroot Private Packet", rendered)
        self.assertIn('"v": "workroot.packet.v1"', rendered)
        self.assertIn('"read_only": true', rendered)
        self.assertIn("Read-only context does not grant a lease", rendered)
        self.assertIn("Sync first before durable commit", rendered)
        self.assertNotIn("workroot agent commit --kind", rendered)

    def test_context_wrapper_does_not_expose_machine_state_or_storage_details(self) -> None:
        rendered = build_context(agent="codex", cwd=self.user_dir, query="Review protocol v2")

        for forbidden in (
            "observed_versions",
            "state_vector",
            "protocol_commit_batches",
            "exchange_leases",
            "workroot.sqlite",
            "cache/workroot.sqlite",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_context_guidance_uses_requested_agent_name(self) -> None:
        rendered = build_context(agent="claude", cwd=self.user_dir, query="Review protocol v2")

        self.assertIn("workroot agent sync --agent claude", rendered)
        self.assertNotIn("workroot agent sync --agent codex", rendered)

    def test_fallback_workroot_guidance_uses_requested_agent_name(self) -> None:
        rendered = workroot_guidance_text(agent="claude")

        self.assertIn("workroot agent sync --agent claude", rendered)
        self.assertNotIn("workroot agent sync --agent codex", rendered)

    def test_context_wrapper_uses_sync_focus_and_does_not_bind_ambiguous_task(self) -> None:
        self.insert_task_graph("task-one", "run-one", "First Task")
        self.insert_task_graph("task-two", "run-two", "Second Task")

        rendered = build_context(agent="codex", cwd=self.user_dir, query="Continue.")

        self.assertIn("Focus: ambiguous", rendered)
        self.assertNotIn("## Current Task", rendered)
        self.assertNotIn("First Task [", rendered)
        self.assertNotIn("Second Task [", rendered)

    def test_context_includes_output_guidance_and_strategy_trace_without_l3_by_default(self) -> None:
        self.insert_task_graph("task-one", "run-one", "Founder Operating Plan")

        rendered = build_context(agent="codex", cwd=self.user_dir, query="Continue Founder Operating Plan", debug=True)

        self.assertIn("## Stable Guidance", rendered)
        self.assertIn("workroot-output", rendered)
        self.assertIn("contextStrategy: plan-driven", rendered)
        self.assertNotIn("disclosureLevels", rendered)
        self.assert_no_internal_disclosure_labels(rendered)

    def test_context_debug_trace_includes_compact_lease_signal_without_internals(self) -> None:
        self.insert_task_graph("task-one", "run-one", "Founder Operating Plan")
        with sqlite3.connect(self.sqlite_path) as conn:
            lease = create_lease(
                conn,
                workroot_id="wr_demo",
                scope="task",
                task_id="task-one",
                run_id="run-one",
                allowed_events=["progress"],
            )
            conn.execute(
                """
                INSERT INTO protocol_events (
                  event_id, batch_id, workroot_id, request_id, lease_id, idempotency_key,
                  kind, schema_version, payload_json, evidence_json, confirmation_json,
                  source_json, occurred_at, received_at, status
                )
                VALUES (
                  'evt-progress-lease-trace', 'batch-lease-trace', 'wr_demo', 'req-lease-trace',
                  ?, 'key-lease-trace', 'progress', 'progress.v1', '{}', '[]', '{}', '{}',
                  '2026-05-28T00:00:00Z', '2026-05-28T00:00:00Z', 'applied'
                )
                """,
                (lease["lease_id"],),
            )
            conn.commit()

        rendered = build_context(agent="codex", cwd=self.user_dir, query="Continue Founder Operating Plan", debug=True)

        self.assertIn("leaseSignal: status=fresh_active freshness=fresh", rendered)
        self.assertNotIn("exchange_leases", rendered)
        self.assertNotIn("policy_json", rendered)
        self.assertNotIn("observed_versions_json", rendered)
        self.assertNotIn("lease-", rendered)

    def test_query_evidence_language_without_work_signal_stays_shallow(self) -> None:
        self.insert_task_graph("task-one", "run-one", "Founder Operating Plan")

        rendered = build_context(
            agent="codex", cwd=self.user_dir, query="Show evidence from Founder Operating Plan", debug=True
        )

        self.assertIn("contextStrategy: plan-driven", rendered)
        self.assertIn("contextIntent: orient", rendered)
        self.assertNotIn("disclosureLevels", rendered)
        self.assert_no_internal_disclosure_labels(rendered)

    def test_context_strategy_uses_explicit_work_signal_for_multilingual_evidence(self) -> None:
        self.insert_task_graph("task-one", "run-one", "Founder Operating Plan")

        rendered = build_context(
            agent="codex",
            cwd=self.user_dir,
            query="继续昨天的定价策略，找一下我们当时为什么决定先不涨价。",
            debug=True,
            work_signal={
                "phase": "orienting",
                "work_kind": "continuation",
                "intended_action": "inspect",
                "focus": "定价策略：先不涨价的依据",
                "concerns": ["needs_evidence"],
            },
        )

        self.assertIn("contextStrategy: plan-driven", rendered)
        self.assertIn("contextIntent: evidence_lookup", rendered)
        self.assertNotIn("disclosureLevels", rendered)
        self.assert_no_internal_disclosure_labels(rendered)

    def test_default_startup_work_signal_does_not_force_l3(self) -> None:
        self.insert_task_graph("task-one", "run-one", "Founder Operating Plan")

        rendered = build_context(
            agent="codex",
            cwd=self.user_dir,
            query="继续昨天的定价策略",
            debug=True,
        )

        self.assertIn("contextStrategy: plan-driven", rendered)
        self.assertNotIn("disclosureLevels", rendered)
        self.assert_no_internal_disclosure_labels(rendered)

    def test_quick_answer_plan_does_not_render_relationships_even_when_candidates_match(self) -> None:
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                INSERT INTO context_candidates (
                  candidate_id, workroot_id, source_type, source_id, title, summary,
                  domains, importance, confidence, status, context_policy, safety_policy,
                  token_estimate, updatedAt, lastUsedAt, use_count
                )
                VALUES (
                  'asset:asset-report', 'wr_demo', 'asset', 'asset-report',
                  'Strategy report', 'Relationship-heavy candidate.',
                  '', 'high', 0.9, 'active', 'task-related', '',
                  20, '2026-05-28T00:00:00Z', '', 0
                )
                """
            )
            conn.execute(
                "INSERT INTO context_candidates_fts (candidate_id, title, summary, domains) VALUES (?, ?, ?, ?)",
                ("asset:asset-report", "Strategy report", "Relationship-heavy candidate.", ""),
            )
            conn.execute(
                """
                INSERT INTO relationship_nodes (node_id, workroot_id, node_type, title, target_type, target_id)
                VALUES ('node-report', 'wr_demo', 'asset', 'Strategy report', 'asset', 'asset-report')
                """
            )
            conn.execute(
                """
                INSERT INTO relationship_nodes (node_id, workroot_id, node_type, title, target_type, target_id)
                VALUES ('node-related', 'wr_demo', 'asset', 'Related material', NULL, NULL)
                """
            )
            conn.execute(
                """
                INSERT INTO relationship_edges (
                  edge_id, workroot_id, from_node_id, to_node_id, relationship_type, confidence, status
                )
                VALUES ('edge-report-related', 'wr_demo', 'node-report', 'node-related', 'related_to', 0.9, 'active')
                """
            )
            conn.commit()

        rendered = build_context(
            agent="codex",
            cwd=self.user_dir,
            query="Answer briefly.",
            debug=True,
            work_signal={
                "phase": "orienting",
                "work_kind": "quick",
                "intended_action": "answer",
                "focus": "Brief answer",
            },
        )

        self.assertIn("contextIntent: answer", rendered)
        self.assertNotIn("relationships", self._debug_recall_sources(rendered))
        self.assertNotIn("## Relationship Signals", rendered)
        self.assertNotIn("edge-report-related", rendered)

    def test_quick_answer_plan_does_not_scan_user_asset_fallback(self) -> None:
        (self.user_dir / "loose.md").write_text("Loose user asset that should not enter quick answer context.\n")

        rendered = build_context(
            agent="codex",
            cwd=self.user_dir,
            query="Answer briefly.",
            debug=True,
            work_signal={
                "phase": "orienting",
                "work_kind": "quick",
                "intended_action": "answer",
                "focus": "Brief answer",
            },
        )

        self.assertIn("contextIntent: answer", rendered)
        self.assertNotIn("fallback_user_assets", self._debug_recall_sources(rendered))
        self.assertNotIn("loose.md", rendered)

    def test_ref_follow_up_selects_referenced_candidate_without_query_keywords(self) -> None:
        self.insert_task_graph("task-one", "run-one", "Founder Operating Plan")
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                INSERT INTO context_candidates (
                  candidate_id, workroot_id, source_type, source_id, title, summary,
                  domains, importance, confidence, status, context_policy, safety_policy,
                  token_estimate, updatedAt, lastUsedAt, use_count
                )
                VALUES (
                  'decision:dec-pricing', 'wr_demo', 'decision', 'dec-pricing',
                  'Pricing decision', 'Keep pricing unchanged until onboarding risk is reduced.',
                  'task:task-one', 'high', 0.9, 'active', 'task-related', '',
                  20, '2026-05-28T00:00:00Z', '', 0
                )
                """
            )
            conn.execute(
                "INSERT INTO context_candidates_fts (candidate_id, title, summary, domains) VALUES (?, ?, ?, ?)",
                (
                    "decision:dec-pricing",
                    "Pricing decision",
                    "Keep pricing unchanged until onboarding risk is reduced.",
                    "task:task-one",
                ),
            )
            conn.commit()

        rendered = build_context(
            agent="codex",
            cwd=self.user_dir,
            query="展开刚才那个决定",
            work_signal={
                "phase": "orienting",
                "work_kind": "continuation",
                "intended_action": "inspect",
                "focus": "刚才那个决定",
                "refs": ["decision:dec-pricing"],
            },
        )

        self.assertIn("Pricing decision", rendered)
        self.assertIn("Ref: decision:dec-pricing", rendered)

    def test_context_retrieval_enforces_current_task_scope_for_candidates_and_hints(self) -> None:
        self.insert_task_graph("task-one", "run-one", "Founder Operating Plan")
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                INSERT INTO context_candidates (
                  candidate_id, workroot_id, source_type, source_id, title, summary,
                  domains, importance, confidence, status, context_policy, safety_policy,
                  token_estimate, updatedAt, lastUsedAt, use_count
                )
                VALUES (
                  'decision:dec-task-one', 'wr_demo', 'decision', 'dec-task-one',
                  'Pricing decision', 'Current task pricing decision.',
                  'task:task-one scope:task', 'normal', 0.8, 'active', 'task-related', '',
                  20, '2026-05-28T00:00:00Z', '', 0
                )
                """
            )
            conn.execute(
                """
                INSERT INTO context_candidates (
                  candidate_id, workroot_id, source_type, source_id, title, summary,
                  domains, importance, confidence, status, context_policy, safety_policy,
                  token_estimate, updatedAt, lastUsedAt, use_count
                )
                VALUES (
                  'decision:dec-task-two', 'wr_demo', 'decision', 'dec-task-two',
                  'Pricing decision', 'Other task pricing decision.',
                  'task:task-two scope:task', 'critical', 0.9, 'active', 'task-related', '',
                  20, '2026-05-28T00:00:00Z', '', 0
                )
                """
            )
            conn.execute(
                "INSERT INTO context_candidates_fts (candidate_id, title, summary, domains) VALUES (?, ?, ?, ?)",
                ("decision:dec-task-one", "Pricing decision", "Current task pricing decision.", "task:task-one"),
            )
            conn.execute(
                "INSERT INTO context_candidates_fts (candidate_id, title, summary, domains) VALUES (?, ?, ?, ?)",
                ("decision:dec-task-two", "Pricing decision", "Other task pricing decision.", "task:task-two"),
            )
            conn.commit()

        rendered = build_context(
            agent="codex",
            cwd=self.user_dir,
            query="Pricing decision",
            work_signal={
                "phase": "orienting",
                "work_kind": "continuation",
                "intended_action": "inspect",
                "focus": "Pricing decision",
            },
        )

        self.assertIn("Current task pricing decision", rendered)
        self.assertNotIn("Other task pricing decision", rendered)

    def test_asset_ref_follow_up_can_render_scoped_evidence_without_query_keywords(self) -> None:
        self.insert_task_graph("task-one", "run-one", "Founder Operating Plan")
        asset_path = self.user_dir / "workroot-output" / "pricing-plan.md"
        asset_path.parent.mkdir(parents=True, exist_ok=True)
        asset_path.write_text(
            "Pricing plan evidence: keep pricing unchanged while onboarding risk remains high.\n",
            encoding="utf-8",
        )
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                INSERT INTO indexed_files (file_id, workroot_id, relative_path, source_type, source_id)
                VALUES ('file-pricing-plan', 'wr_demo', 'workroot-output/pricing-plan.md', 'asset', 'asset-pricing')
                """
            )
            conn.execute(
                """
                INSERT INTO indexed_chunks (chunk_id, file_id, workroot_id, body)
                VALUES (
                  'file-pricing-plan:chunk:0',
                  'file-pricing-plan',
                  'wr_demo',
                  'Pricing plan evidence: keep pricing unchanged while onboarding risk remains high.'
                )
                """
            )
            conn.execute(
                "INSERT INTO indexed_chunks_fts (chunk_id, body) VALUES (?, ?)",
                (
                    "file-pricing-plan:chunk:0",
                    "Pricing plan evidence: keep pricing unchanged while onboarding risk remains high.",
                ),
            )
            conn.commit()

        rendered = build_context(
            agent="codex",
            cwd=self.user_dir,
            query="展开这个文件的依据",
            work_signal={
                "phase": "orienting",
                "work_kind": "continuation",
                "intended_action": "inspect",
                "focus": "这个文件的依据",
                "refs": ["asset:asset-pricing"],
            },
        )

        self.assertIn("## Evidence", rendered)
        self.assertIn("workroot-output/pricing-plan.md", rendered)

    def test_context_work_signal_drops_invalid_refs_before_strategy(self) -> None:
        rendered = build_context(
            agent="codex",
            cwd=self.user_dir,
            query="展开这个引用",
            debug=True,
            work_signal={
                "phase": "orienting",
                "work_kind": "continuation",
                "intended_action": "inspect",
                "focus": "这个引用",
                "refs": ["asset:bad/path"],
            },
        )

        self.assertNotIn("disclosureLevels", rendered)
        self.assert_no_internal_disclosure_labels(rendered)

    def test_visible_context_does_not_expose_internal_disclosure_or_process_labels(self) -> None:
        self.insert_task_graph("task-one", "run-one", "Founder Operating Plan")

        rendered = build_context(agent="codex", cwd=self.user_dir, query="Continue Founder Operating Plan")

        self.assertIn("## Current Task", rendered)
        self.assertIn("- Founder Operating Plan", rendered)
        self.assertNotIn("[active; task; L1]", rendered)
        self.assertNotIn("processLevel", rendered)
        self.assertNotIn("disclosureLevels", rendered)
        self.assert_no_internal_disclosure_labels(rendered)

    def count_rows(self, *tables: str) -> dict[str, int]:
        with sqlite3.connect(self.sqlite_path) as conn:
            return {table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables}

    def _debug_recall_sources(self, rendered: str) -> str:
        for line in rendered.splitlines():
            if line.startswith("recallSources: "):
                return line
        return ""

    def assert_no_internal_disclosure_labels(self, rendered: str) -> None:
        self.assertNotRegex(rendered, r"\bL[123]\b")

    def insert_task_graph(self, task_id: str, run_id: str, title: str) -> None:
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                INSERT INTO tasks (
                  task_id, workroot_id, title, status, task_kind, process_level, role,
                  root_task_id, retention_policy, visibility, created_at, updated_at
                )
                VALUES (?, 'wr_demo', ?, 'active', 'task', 'L1', 'normal', ?, 'until_closed', 'normal',
                        '2026-05-28T00:00:00Z', '2026-05-28T00:00:00Z')
                """,
                (task_id, title, task_id),
            )
            conn.execute(
                """
                INSERT INTO task_runs (
                  run_id, task_id, workroot_id, agent_name, status, goal, input_summary,
                  output_summary, source_lease_id, started_at
                )
                VALUES (?, ?, 'wr_demo', 'codex', 'active', ?, ?, ?, '', '2026-05-28T00:00:00Z')
                """,
                (run_id, task_id, title, title, f"{title} summary"),
            )
            conn.commit()


if __name__ == "__main__":
    unittest.main()
