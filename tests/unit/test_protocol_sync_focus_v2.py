from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.protocol.controller import sync
from ai_workroot.state.environment import initialize_environment, register_workroot
from ai_workroot.state.layout import workroot_sqlite_path
from ai_workroot.state.sqlite import initialize_workroot_sqlite


class ProtocolSyncFocusV2Test(unittest.TestCase):
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

    def test_sync_unavailable_returns_non_blocking_not_recorded_response(self) -> None:
        response = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-unavailable",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(Path(self.tmp.name) / "outside-workroot"),
                "reason": "before_work",
                "query": "Continue helping.",
            }
        )

        self.assertTrue(response["ok"])
        self.assertTrue(response["agent_may_continue"])
        self.assertEqual(response["workroot_view"]["focus"], "unavailable")
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "sync")
        self.assertEqual(response["result"]["status"], "not_recorded")
        self.assertFalse(response["workroot_contract"]["commit_contract"]["durable_commit_allowed"])
        self.assertIsNone(response["workroot_contract"]["commit_contract"]["lease_id"])

    def test_quick_signal_plus_quick_query_returns_answer_without_persistence(self) -> None:
        response = self.sync_request(
            request_id="req-sync-quick",
            query="Explain lease in one sentence.",
            work_signal={"phase": "starting", "work_kind": "quick", "intended_action": "answer"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "quick")
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "none")
        self.assertFalse(response["workroot_contract"]["commit_contract"]["durable_commit_allowed"])
        self.assertEqual(self.count_rows("exchange_leases"), 0)

    def test_durable_query_markers_override_erroneous_quick_signal(self) -> None:
        response = self.sync_request(
            request_id="req-sync-durable-overrides-quick",
            query="Start durable work to design the Workroot Agent protocol implementation and break down the test plan.",
            work_signal={"phase": "starting", "work_kind": "quick", "intended_action": "answer"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "new_work")
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "commit")
        self.assertTrue(response["workroot_contract"]["commit_contract"]["durable_commit_allowed"])

    def test_structured_durable_signal_is_treated_as_new_work(self) -> None:
        response = self.sync_request(
            request_id="req-sync-durable-language",
            query="Six-week pricing and onboarding cadence",
            work_signal={"phase": "planning", "work_kind": "task", "intended_action": "plan"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "new_work")
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "commit")
        self.assertTrue(response["workroot_contract"]["commit_contract"]["durable_commit_allowed"])
        self.assertIn("intent", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])
        self.assertIsNotNone(response["workroot_contract"]["commit_contract"]["lease_id"])

    def test_durable_followup_prefers_current_active_task(self) -> None:
        self.insert_task_graph(
            task_id="task-founder-cadence",
            run_id="run-founder-cadence",
            title="Six-week pricing and onboarding cadence",
            summary="Founder is building a pricing and onboarding operating cadence.",
            handoff_next_action="Review the founder operating plan and update the next checkpoint.",
        )

        response = self.sync_request(
            request_id="req-sync-durable-followup",
            reason="before_work",
            query="Review the founder operating plan and update the risk checkpoint.",
            work_signal={"phase": "executing", "work_kind": "task", "intended_action": "review"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "continuation")
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "commit")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-founder-cadence")
        self.assertEqual(response["workroot_contract"]["state_refs"]["run_ref"], "run-founder-cadence")
        self.assertNotIn("intent", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])

    def test_decision_followup_continues_active_task_and_allows_decision_and_asset(self) -> None:
        self.insert_task_graph(
            task_id="task-founder-cadence",
            run_id="run-founder-cadence",
            title="Six-week pricing and onboarding cadence",
            summary="Founder is building a pricing and onboarding operating cadence.",
            handoff_next_action="Choose the next pricing guardrail.",
        )

        response = self.sync_request(
            request_id="req-sync-decision-followup",
            reason="before_work",
            query="choose first pricing guardrail",
            work_signal={"phase": "deciding", "work_kind": "decision", "intended_action": "decide"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "continuation")
        allowed = response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"]
        self.assertIn("decision", allowed)
        self.assertIn("asset", allowed)
        self.assertIn("progress", allowed)
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-founder-cadence")

    def test_decision_followup_uses_semantic_plural_match_to_choose_task(self) -> None:
        self.insert_task_graph(
            task_id="task-metrics",
            run_id="run-metrics",
            title="Metrics continuity investigation",
            summary="Inspect metrics.csv signal fields and map them to task continuity and asset recall quality.",
            handoff_next_action="Inspect metrics.csv and map signal fields to task continuity and asset recall quality.",
        )
        self.insert_task_graph(
            task_id="task-interviews",
            run_id="run-interviews",
            title="Customer interview task",
            summary="Run interviews to validate the first value moment before pricing.",
            handoff_next_action="Run interviews to validate the first value moment before pricing.",
        )
        self.insert_task_graph(
            task_id="task-runtime-views",
            run_id="run-runtime-views",
            title="Runtime view decision task",
            summary="Keep rebuildable runtime views derived from canonical records.",
            handoff_next_action="Apply the runtime view decision in future indexing changes.",
        )

        response = self.sync_request(
            request_id="req-sync-decision-metric-singular",
            reason="continue",
            query="Make a stable decision about which metric should drive the next validation pass.",
            work_signal={"phase": "deciding", "work_kind": "decision", "intended_action": "decide"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "continuation")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-metrics")
        self.assertIn("decision", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])

    def test_start_temporary_inbox_is_new_work_even_with_active_task(self) -> None:
        self.insert_task_graph(
            task_id="task-founder-cadence",
            run_id="run-founder-cadence",
            title="Six-week pricing and onboarding cadence",
            summary="Founder is building a pricing and onboarding operating cadence.",
            handoff_next_action="Continue the operating cadence.",
        )

        response = self.sync_request(
            request_id="req-sync-temporary-inbox-start",
            reason="after_error",
            query="start temporary onboarding language inbox",
            work_signal={"phase": "switching", "work_kind": "inbox", "intended_action": "preserve"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "new_work")
        self.assertIn("intent", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], None)

    def test_switching_inbox_signal_is_new_work_even_when_action_is_unknown(self) -> None:
        self.insert_task_graph(
            task_id="task-founder-cadence",
            run_id="run-founder-cadence",
            title="Founder operating task",
            summary="Founder operating task.",
            handoff_next_action="Continue founder work.",
        )

        response = self.sync_request(
            request_id="req-sync-switching-inbox-unknown-action",
            reason="before_task_switch",
            query="loose inbox thread",
            work_signal={
                "phase": "switching",
                "work_kind": "inbox",
                "intended_action": "start loose thread",
            },
        )

        self.assertEqual(response["workroot_view"]["focus"], "new_work")
        self.assertIn("intent", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], None)

    def test_switching_task_decision_prefers_existing_task_not_new_root(self) -> None:
        self.insert_task_graph(
            task_id="task-engineering-continuity",
            run_id="run-engineering-continuity",
            title="Protocol continuity engineering task",
            summary="Inspect protocol continuity, runtime views, and asset indexing behavior.",
            handoff_next_action="Record the runtime view decision.",
        )

        response = self.sync_request(
            request_id="req-sync-switching-task-decision",
            reason="before_work",
            query="Make engineering decision: runtime views rebuildable rather than canonical",
            work_signal={
                "phase": "switching",
                "work_kind": "task",
                "intended_action": "decide",
                "focus": "runtime views rebuildable rather than canonical",
            },
        )

        self.assertEqual(response["workroot_view"]["focus"], "continuation")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-engineering-continuity")
        self.assertIn("decision", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])
        self.assertNotIn("intent", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])

    def test_start_durable_task_phrase_is_new_work_even_with_active_task(self) -> None:
        self.insert_task_graph(
            task_id="task-founder-cadence",
            run_id="run-founder-cadence",
            title="Founder operating task",
            summary="Founder operating task.",
            handoff_next_action="Continue founder work.",
        )

        response = self.sync_request(
            request_id="req-sync-start-durable-inspection",
            reason="after_error",
            query="start durable inspection task",
            work_signal={"phase": "switching", "work_kind": "task", "intended_action": "plan"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "new_work")
        self.assertIn("intent", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])

    def test_start_durable_task_with_source_file_reference_is_new_work(self) -> None:
        self.insert_task_graph(
            task_id="task-operating",
            run_id="run-operating",
            title="Operating task",
            summary="Schedule interviews and update operating follow-up.",
            handoff_next_action="Schedule interviews and update operating follow-up.",
        )
        self.insert_task_graph(
            task_id="task-engineering",
            run_id="run-engineering",
            title="Engineering task",
            summary="Inspect continuity and asset recall behavior.",
            handoff_next_action="Inspect continuity and asset recall behavior.",
        )

        response = self.sync_request(
            request_id="req-sync-start-task-with-source-file-reference",
            reason="before_task_switch",
            query="Start a third durable investigation task to connect metrics.csv signals to task continuity and asset recall quality.",
            work_signal={"phase": "switching", "work_kind": "task", "intended_action": "plan"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "new_work")
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "commit")
        self.assertIn("intent", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])
        self.assertIsNotNone(response["workroot_contract"]["commit_contract"]["lease_id"])

    def test_quick_answer_query_overrides_erroneous_task_signal(self) -> None:
        self.insert_task_graph(
            task_id="task-current",
            run_id="run-current",
            title="Current task",
            summary="Current task summary.",
            handoff_next_action="Continue current task.",
        )

        response = self.sync_request(
            request_id="req-sync-quick-overrides-task-signal",
            reason="before_task_switch",
            query="Quick answer only: contrast a checkpoint with an asset in one sentence.",
            work_signal={"phase": "switching", "work_kind": "task", "intended_action": "plan"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "quick")
        self.assertFalse(response["workroot_contract"]["commit_contract"]["durable_commit_allowed"])
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], None)

    def test_handoff_request_with_erroneous_task_signal_continues_existing_task(self) -> None:
        self.insert_task_graph(
            task_id="task-current",
            run_id="run-current",
            title="Current task",
            summary="Current task summary.",
            handoff_next_action="Continue current task.",
        )

        response = self.sync_request(
            request_id="req-sync-handoff-overrides-task-signal",
            reason="before_task_switch",
            query="Preserve a final handoff that tells the next agent how to continue across active tasks.",
            work_signal={
                "phase": "switching",
                "work_kind": "task",
                "intended_action": "plan",
                "focus": "final cross-task handoff",
            },
        )

        self.assertEqual(response["workroot_view"]["focus"], "continuation")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-current")
        self.assertIn("handoff", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])
        self.assertNotIn("intent", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])

    def test_continue_temporary_inbox_prefers_existing_inbox_task(self) -> None:
        self.insert_task_graph(
            task_id="task-founder-cadence",
            run_id="run-founder-cadence",
            title="Founder pricing, onboarding risk, and context continuity operating task",
            summary="Founder operating task.",
            handoff_next_action="Continue the founder operating cadence.",
        )
        self.insert_task_graph(
            task_id="task-onboarding-inbox",
            run_id="run-onboarding-inbox",
            title="Onboarding language loose questions inbox",
            summary="Temporary inbox for onboarding language.",
            handoff_next_action="",
            role="inbox",
            process_level="L0",
        )

        response = self.sync_request(
            request_id="req-sync-continue-temporary-inbox",
            reason="before_work",
            query="Continue the temporary inbox thread and preserve one lightweight checkpoint.",
            work_signal={"phase": "preserving", "work_kind": "inbox", "intended_action": "preserve"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "continuation")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-onboarding-inbox")
        self.assertIn("progress", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])

    def test_continue_query_that_names_inbox_prefers_existing_inbox_over_current_handoff(self) -> None:
        self.insert_task_graph(
            task_id="task-active-normal",
            run_id="run-active-normal",
            title="Active normal work",
            summary="Current normal work has a recent handoff.",
            handoff_next_action="Continue the normal work.",
        )
        self.insert_task_graph(
            task_id="task-loose-inbox",
            run_id="run-loose-inbox",
            title="Temporary inbox: onboarding language",
            summary="",
            handoff_next_action="",
            role="inbox",
            process_level="L0",
        )

        response = self.sync_request(
            request_id="req-sync-continue-named-inbox",
            reason="continue",
            query="Continue the temporary inbox thread and preserve one lightweight checkpoint.",
            work_signal={"phase": "recovering", "work_kind": "continuation", "intended_action": "preserve"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "continuation")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-loose-inbox")
        self.assertIn("progress", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])

    def test_return_to_founder_task_prefers_matching_normal_task_over_inbox(self) -> None:
        self.insert_task_graph(
            task_id="task-founder-cadence",
            run_id="run-founder-cadence",
            title="Founder pricing, onboarding risk, and context continuity operating task",
            summary="Founder operating task.",
            handoff_next_action="Continue the founder operating cadence.",
        )
        self.insert_task_graph(
            task_id="task-onboarding-inbox",
            run_id="run-onboarding-inbox",
            title="Onboarding language loose questions inbox",
            summary="Temporary inbox for onboarding language.",
            handoff_next_action="",
            role="inbox",
            process_level="L0",
        )

        response = self.sync_request(
            request_id="req-sync-return-founder",
            reason="before_work",
            query="Return to the durable founder operating task and preserve a checkpoint.",
            work_signal={"phase": "preserving", "work_kind": "task", "intended_action": "preserve"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "continuation")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-founder-cadence")

    def test_continue_query_title_match_prefers_named_task_over_related_handoff(self) -> None:
        self.insert_task_graph(
            task_id="task-operating-thread",
            run_id="run-operating-thread",
            title="Operating thread",
            summary="Current operating work.",
            handoff_next_action="Switch to the related implementation task when needed.",
        )
        self.insert_task_graph(
            task_id="task-engineering-inspection",
            run_id="run-engineering-inspection",
            title="Protocol Continuity Engineering Inspection",
            summary="Inspect protocol continuity, runtime views, and asset indexing behavior.",
            handoff_next_action="Inspect protocol continuity, runtime views, and asset indexing behavior.",
        )

        response = self.sync_request(
            request_id="req-sync-named-engineering-task",
            reason="continue",
            query="Continue engineering task and checkpoint most important implementation risk.",
            work_signal={
                "phase": "planning",
                "work_kind": "continuation",
                "intended_action": "preserve",
                "focus": "engineering checkpoint: implementation risk",
            },
        )

        self.assertEqual(response["workroot_view"]["focus"], "continuation")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-engineering-inspection")

    def test_new_task_signal_returns_to_existing_matching_task(self) -> None:
        self.insert_task_graph(
            task_id="task-founder-cadence",
            run_id="run-founder-cadence",
            title="Durable founder operating task",
            summary="Founder operating thread for customer interview sequencing and pricing guardrails.",
            handoff_next_action="Run the next customer interview batch.",
        )
        self.insert_task_graph(
            task_id="task-onboarding-inbox",
            run_id="run-onboarding-inbox",
            title="Onboarding language loose questions inbox",
            summary="Temporary inbox for onboarding language.",
            handoff_next_action="",
            role="inbox",
            process_level="L0",
        )

        response = self.sync_request(
            request_id="req-sync-return-existing-even-if-new-signal",
            reason="before_task_switch",
            query="Return to the durable founder operating task and preserve a checkpoint about customer interview sequencing.",
            work_signal={"phase": "switching", "work_kind": "task", "intended_action": "plan"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "continuation")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-founder-cadence")
        self.assertIn("progress", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])
        self.assertNotIn("intent", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])

    def test_empty_new_task_signal_prefers_existing_continuation(self) -> None:
        self.insert_task_graph(
            task_id="task-founder-cadence",
            run_id="run-founder-cadence",
            title="Founder operating task",
            summary="Founder operating task.",
            handoff_next_action="Continue founder work.",
        )

        response = self.sync_request(
            request_id="req-sync-empty-new-task-signal",
            reason="before_task_switch",
            query="",
            work_signal={"phase": "switching", "work_kind": "task", "intended_action": "plan"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "continuation")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-founder-cadence")
        self.assertNotIn("intent", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])

    def test_new_task_signal_for_existing_asset_prefers_owning_task(self) -> None:
        self.insert_task_graph(
            task_id="task-founder-cadence",
            run_id="run-founder-cadence",
            title="Founder operating task",
            summary="Founder operating task.",
            handoff_next_action="Continue founder work.",
        )
        self.insert_task_asset(
            task_id="task-founder-cadence",
            asset_id="asset-operating-brief",
            title="Operating Brief",
            path="results/operating-brief.md",
        )

        response = self.sync_request(
            request_id="req-sync-existing-asset-new-task-signal",
            reason="before_task_switch",
            query="Update results/operating-brief.md with the customer interview sequencing checkpoint.",
            work_signal={"phase": "switching", "work_kind": "task", "intended_action": "plan"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "continuation")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-founder-cadence")
        self.assertIn("asset", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])
        self.assertNotIn("intent", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])

    def test_new_task_signal_for_new_asset_prefers_current_task_continuation(self) -> None:
        self.insert_task_graph(
            task_id="task-current-plan",
            run_id="run-current-plan",
            title="Current planning task",
            summary="Current task tracks a plan and its supporting user-visible outputs.",
            handoff_next_action="Create the next planning asset.",
        )

        response = self.sync_request(
            request_id="req-sync-new-asset-under-current-task",
            reason="before_task_switch",
            query="Create results/action-plan.md with the next plan and preserve it as an asset.",
            work_signal={"phase": "switching", "work_kind": "task", "intended_action": "plan"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "continuation")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-current-plan")
        self.assertIn("asset", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])
        self.assertNotIn("intent", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])

    def test_new_asset_with_multiple_tasks_uses_workroot_scope_when_owner_unclear(self) -> None:
        self.insert_task_graph(
            task_id="task-founder",
            run_id="run-founder",
            title="Founder task",
            summary="Founder task summary.",
            handoff_next_action="Continue founder work.",
        )
        self.insert_task_graph(
            task_id="task-engineering",
            run_id="run-engineering",
            title="Engineering task",
            summary="Runtime views are rebuildable projections, not canonical state.",
            handoff_next_action="Keep durable events authoritative before implementation resumes.",
        )
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                UPDATE tasks
                SET updated_at = '2026-05-29T00:00:00Z'
                WHERE task_id = 'task-engineering'
                """
            )
            conn.execute(
                """
                UPDATE handoffs
                SET created_at = '2026-05-29T00:00:00Z'
                WHERE task_id = 'task-engineering'
                """
            )
            conn.commit()

        response = self.sync_request(
            request_id="req-sync-new-asset-no-clear-owner",
            reason="before_task_switch",
            query="Create docs/technical-risk-note.md with a compact risk note and preserve it as an asset.",
            work_signal={"phase": "switching", "work_kind": "task", "intended_action": "plan"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "workroot_capture")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], None)
        self.assertEqual(response["workroot_contract"]["state_refs"]["run_ref"], None)
        self.assertIn("asset", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])
        self.assertNotIn("intent", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])

    def test_new_asset_with_explicit_task_language_binds_owner(self) -> None:
        self.insert_task_graph(
            task_id="task-founder",
            run_id="run-founder",
            title="Founder task",
            summary="Founder task summary.",
            handoff_next_action="Continue founder work.",
        )
        self.insert_task_graph(
            task_id="task-engineering",
            run_id="run-engineering",
            title="Engineering continuity task",
            summary="Inspect protocol continuity, runtime views, and asset indexing behavior.",
            handoff_next_action="Keep durable events authoritative before implementation resumes.",
        )

        response = self.sync_request(
            request_id="req-sync-new-asset-clear-owner",
            reason="before_task_switch",
            query=(
                "Create an engineering continuity task asset at docs/technical-risk-note.md "
                "with a compact risk note and preserve it."
            ),
            work_signal={"phase": "switching", "work_kind": "task", "intended_action": "plan"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "continuation")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-engineering")
        self.assertIn("asset", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])

    def test_asset_task_qualifier_uses_run_goal_when_titles_share_generic_terms(self) -> None:
        self.insert_task_graph(
            task_id="task-founder",
            run_id="run-founder",
            title="Founder Operating Thread: Pricing, Onboarding Risk, Context Continuity",
            summary="Founder operating task summary.",
            handoff_next_action="Run five activation-focused founder interviews.",
            run_goal="Durable founder task for pricing, onboarding risk, and context continuity.",
        )
        self.insert_task_graph(
            task_id="task-engineering",
            run_id="run-engineering",
            title="Inspect protocol continuity and indexing",
            summary="No further action needed for this round.",
            handoff_next_action="Apply the runtime view decision in future indexing changes.",
            run_goal="Separate durable engineering task opened to inspect protocol continuity, runtime views, and asset indexing behavior.",
        )
        self.insert_task_graph(
            task_id="task-metrics",
            run_id="run-metrics",
            title="Metrics Continuity Investigation",
            summary="Metrics task summary.",
            handoff_next_action="Run the next validation pass around asset recall failure modes.",
            run_goal="Metrics investigation for continuity quality and asset recall quality.",
        )

        response = self.sync_request(
            request_id="req-sync-asset-qualifier-run-goal",
            reason="before_task_switch",
            query="Create engineering continuity task asset at docs/technical-risk-note.md",
            work_signal={"phase": "switching", "work_kind": "task", "intended_action": "plan"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "continuation")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-engineering")
        self.assertIn("asset", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])

    def test_cross_task_asset_request_uses_workroot_scope_without_task_owner(self) -> None:
        self.insert_task_graph(
            task_id="task-founder",
            run_id="run-founder",
            title="Founder task",
            summary="Founder task summary.",
            handoff_next_action="Run activated-user interviews focused on value proof and asset recall.",
        )
        self.insert_task_graph(
            task_id="task-metrics",
            run_id="run-metrics",
            title="Metrics investigation",
            summary="Metrics investigation summary.",
            handoff_next_action=(
                "Next agent should run the activated-user asset recall validation pass "
                "and keep cross-task continuity aligned."
            ),
        )

        response = self.sync_request(
            request_id="req-sync-cross-task-summary-asset",
            reason="before_task_switch",
            query="Create results/executive-summary.md with the final cross-task summary and preserve it as an asset.",
            work_signal={"phase": "switching", "work_kind": "task", "intended_action": "plan"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "workroot_capture")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], None)
        self.assertEqual(response["workroot_contract"]["state_refs"]["run_ref"], None)
        self.assertIn("asset", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])
        self.assertNotIn("intent", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])

    def test_inbox_continuation_prefers_existing_inbox_over_close_normal_match(self) -> None:
        self.insert_task_graph(
            task_id="task-founder",
            run_id="run-founder",
            title="Founder operating task",
            summary="Founder operating task summary.",
            handoff_next_action="Preserve one lightweight checkpoint for the current operating thread.",
        )
        self.insert_task_graph(
            task_id="task-loose-inbox",
            run_id="run-loose-inbox",
            title="Loose onboarding language questions",
            summary="Loose onboarding language questions",
            handoff_next_action="",
            role="inbox",
            process_level="L0",
        )

        response = self.sync_request(
            request_id="req-sync-close-inbox-focus",
            reason="continue",
            query="Continue the temporary inbox thread and preserve one lightweight checkpoint.",
            work_signal={"work_kind": "continuation", "intended_action": "plan"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "continuation")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-loose-inbox")
        self.assertIn("progress", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])

    def test_asset_request_prefers_best_related_task_when_candidates_are_close(self) -> None:
        self.insert_task_graph(
            task_id="task-operating",
            run_id="run-operating",
            title="Operating task",
            summary="Operating task summary.",
            handoff_next_action="Interview customer accounts, then compare findings against stalled accounts.",
        )
        self.insert_task_graph(
            task_id="task-engineering",
            run_id="run-engineering",
            title="Engineering task",
            summary="Engineering task summary.",
            handoff_next_action="Inspect protocol continuity, runtime views, and asset indexing behavior in the task.",
        )
        self.insert_task_graph(
            task_id="task-records",
            run_id="run-records",
            title="Records task",
            summary="Records task summary.",
            handoff_next_action="Use source records and events as the authority for runtime views.",
        )

        response = self.sync_request(
            request_id="req-sync-close-asset-focus",
            reason="before_task_switch",
            query="Create results/customer-interview-plan.md with a short plan and preserve it as an asset.",
            work_signal={"phase": "switching", "work_kind": "task", "intended_action": "plan"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "continuation")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-operating")
        self.assertIn("asset", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])

    def test_engineering_decision_uses_task_run_goal_when_handoff_candidates_are_close(self) -> None:
        self.insert_task_graph(
            task_id="task-founder",
            run_id="run-founder",
            title="Operating implementation task",
            summary="Founder task summary.",
            handoff_next_action="Define activation event and instrumentation contract.",
            run_goal="Founder operating work for pricing, onboarding, and activation instrumentation.",
        )
        self.insert_task_graph(
            task_id="task-engineering",
            run_id="run-engineering",
            title="Inspect protocol continuity and asset indexing",
            summary="No further action needed for this round.",
            handoff_next_action="No further action needed for this round.",
            run_goal="Durable engineering task to inspect protocol continuity, runtime views, and asset indexing.",
        )
        self.insert_task_graph(
            task_id="task-metrics",
            run_id="run-metrics",
            title="Metrics investigation",
            summary="Metrics task summary.",
            handoff_next_action="Preserve missed-recall examples and keep willingness-to-pay capture gated post-activation.",
            run_goal="Metrics investigation for continuity quality and asset recall quality.",
        )

        response = self.sync_request(
            request_id="req-sync-engineering-decision-goal",
            reason="before_task_switch",
            query="Make a stable engineering decision about keeping runtime views rebuildable rather than canonical.",
            work_signal={
                "phase": "deciding",
                "work_kind": "decision",
                "intended_action": "decide",
                "focus": "runtime view persistence policy",
            },
        )

        self.assertEqual(response["workroot_view"]["focus"], "continuation")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-engineering")
        self.assertIn("decision", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])

    def test_engineering_checkpoint_uses_task_run_goal_when_signal_values_are_tolerated(self) -> None:
        self.insert_task_graph(
            task_id="task-founder",
            run_id="run-founder",
            title="Operating implementation task",
            summary="Founder task summary.",
            handoff_next_action="Define activation event and instrumentation contract.",
            run_goal="Founder operating work for pricing, onboarding, and activation instrumentation.",
        )
        self.insert_task_graph(
            task_id="task-engineering",
            run_id="run-engineering",
            title="Inspect protocol continuity and asset indexing",
            summary="No further action needed for this round.",
            handoff_next_action="No further action needed for this round.",
            run_goal="Durable engineering task to inspect protocol continuity, runtime views, and asset indexing.",
        )
        self.insert_task_graph(
            task_id="task-metrics",
            run_id="run-metrics",
            title="Metrics investigation",
            summary="Metrics task summary.",
            handoff_next_action="Preserve missed-recall examples and keep willingness-to-pay capture gated post-activation.",
            run_goal="Metrics investigation for continuity quality and asset recall quality.",
        )

        response = self.sync_request(
            request_id="req-sync-engineering-checkpoint-goal",
            reason="continue",
            query=(
                "Resume engineering continuity task and preserve checkpoint about whether "
                "FTS and runtime views are enough for inspection"
            ),
            work_signal={"phase": "continuing", "work_kind": "continuation", "intended_action": "checkpoint"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "continuation")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-engineering")
        self.assertIn("progress", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])

    def test_task_qualifier_selects_named_task_over_content_overlap(self) -> None:
        self.insert_task_graph(
            task_id="task-founder",
            run_id="run-founder",
            title="Founder operating task with implementation risk",
            summary="Founder operating task summary.",
            handoff_next_action="Carry forward the activation-first pricing guardrail risk.",
            run_goal="Founder operating work for pricing, onboarding, and activation instrumentation.",
        )
        self.insert_task_graph(
            task_id="task-engineering",
            run_id="run-engineering",
            title="Inspect protocol continuity and indexing",
            summary="Engineering task summary.",
            handoff_next_action="No further action needed for this round.",
            run_goal="Durable engineering task to inspect protocol continuity, runtime views, and asset indexing.",
        )

        response = self.sync_request(
            request_id="req-sync-task-qualifier",
            reason="continue",
            query="Continue the engineering task and preserve a checkpoint with the most important implementation risk.",
            work_signal={"phase": "switching", "work_kind": "continuation", "intended_action": "plan"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "continuation")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-engineering")
        self.assertIn("progress", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])

    def test_decision_like_task_signal_continues_existing_task_without_new_boundary(self) -> None:
        self.insert_task_graph(
            task_id="task-founder",
            run_id="run-founder",
            title="Founder operating thread: pricing, onboarding risk, context continuity",
            summary="Founder operating task summary.",
            handoff_next_action="Continue pricing and onboarding risk work.",
            run_goal="Durable long-cycle founder operating task to track pricing work and onboarding risk.",
        )

        response = self.sync_request(
            request_id="req-sync-decision-like-task-signal",
            reason="before_task_switch",
            query="Make a stable decision about the first pricing guardrail to test and preserve the reason.",
            work_signal={
                "phase": "switching",
                "work_kind": "task",
                "intended_action": "plan",
                "focus": "choose first pricing guardrail to test",
            },
        )

        self.assertEqual(response["workroot_view"]["focus"], "continuation")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-founder")
        self.assertIn("decision", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])
        self.assertNotIn("intent", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])

    def test_query_text_without_work_signal_does_not_create_task_facts(self) -> None:
        response = self.sync_request(
            request_id="req-sync-query-only",
            query="start six-week pricing and onboarding cadence",
        )

        self.assertEqual(response["workroot_view"]["focus"], "quick")
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "none")
        self.assertFalse(response["workroot_contract"]["commit_contract"]["durable_commit_allowed"])
        self.assertEqual(self.count_rows("exchange_leases"), 0)

    def test_structured_task_signal_survives_model_query_compression(self) -> None:
        cases = [
            ("task", "plan"),
            ("investigation", "inspect"),
            ("implementation", "edit"),
        ]
        for index, (work_kind, intended_action) in enumerate(cases, start=1):
            with self.subTest(work_kind=work_kind, intended_action=intended_action):
                response = self.sync_request(
                    request_id=f"req-sync-compressed-{index}",
                    query="short intent",
                    work_signal={
                        "phase": "planning",
                        "work_kind": work_kind,
                        "intended_action": intended_action,
                    },
                )

                self.assertEqual(response["workroot_view"]["focus"], "new_work")
                self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "commit")
                self.assertTrue(response["workroot_contract"]["commit_contract"]["durable_commit_allowed"])
                self.assertIsNotNone(response["workroot_contract"]["commit_contract"]["lease_id"])

    def test_continue_without_known_state_uses_latest_current_handoff(self) -> None:
        self.insert_task_graph(
            task_id="task-protocol",
            run_id="run-protocol",
            title="Protocol v2",
            summary="Response clean break is implemented.",
            handoff_next_action="Continue with commit reliability.",
        )

        response = self.sync_request(
            request_id="req-sync-continue-handoff",
            reason="continue",
            query="Continue yesterday's protocol task.",
        )

        self.assertEqual(response["workroot_view"]["focus"], "continuation")
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "commit")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-protocol")
        self.assertEqual(response["workroot_contract"]["state_refs"]["run_ref"], "run-protocol")
        self.assertIn("Continue with commit reliability.", response["workroot_view"]["next_action"])
        self.assertTrue(response["workroot_contract"]["commit_contract"]["durable_commit_allowed"])

    def test_continue_without_known_state_uses_latest_active_run(self) -> None:
        self.insert_task_graph(
            task_id="task-active",
            run_id="run-active",
            title="Active Task",
            summary="Active run should be resumable.",
            handoff_next_action="",
        )

        response = self.sync_request(
            request_id="req-sync-continue-active-run",
            reason="continue",
            query="Continue.",
        )

        self.assertEqual(response["workroot_view"]["focus"], "continuation")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-active")
        self.assertEqual(response["workroot_contract"]["state_refs"]["run_ref"], "run-active")
        self.assertIn("Active run should be resumable.", response["workroot_view"]["task_brief"])

    def test_invalid_known_state_does_not_claim_active_task(self) -> None:
        response = self.sync_request(
            request_id="req-sync-invalid-known-state",
            reason="continue",
            query="Continue.",
            known_state={"task_id": "task-missing", "run_id": "run-missing"},
        )

        self.assertNotEqual(response["workroot_contract"]["state_refs"].get("task_ref"), "task-missing")
        self.assertFalse(response["workroot_contract"]["commit_contract"]["durable_commit_allowed"])

    def test_ambiguous_focus_defaults_to_continue_without_persistence(self) -> None:
        self.insert_task_graph("task-one", "run-one", "One", "First task.", "")
        self.insert_task_graph("task-two", "run-two", "Two", "Second task.", "")

        response = self.sync_request(
            request_id="req-sync-ambiguous",
            reason="continue",
            query="Continue.",
        )

        self.assertEqual(response["workroot_view"]["focus"], "ambiguous")
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "none")
        self.assertFalse(response["workroot_contract"]["commit_contract"]["durable_commit_allowed"])

    def test_guarded_action_asks_user_and_mints_no_lease(self) -> None:
        response = self.sync_request(
            request_id="req-sync-guarded",
            query="Publish this result.",
            work_signal={"phase": "deciding", "work_kind": "operations", "intended_action": "publish"},
        )

        self.assertEqual(response["workroot_view"]["focus"], "guarded_action")
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "none")
        self.assertFalse(response["workroot_contract"]["commit_contract"]["durable_commit_allowed"])
        self.assertEqual(self.count_rows("exchange_leases"), 0)

    def sync_request(
        self,
        *,
        request_id: str,
        query: str,
        reason: str = "before_work",
        known_state: dict[str, object] | None = None,
        work_signal: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": request_id,
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": reason,
                "query": query,
                "known_state": known_state or {},
                "work_signal": work_signal or {},
            }
        )

    def insert_task_graph(
        self,
        task_id: str,
        run_id: str,
        title: str,
        summary: str,
        handoff_next_action: str,
        *,
        role: str = "normal",
        process_level: str = "L1",
        run_goal: str | None = None,
    ) -> None:
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                INSERT INTO tasks (
                  task_id, workroot_id, title, status, task_kind, process_level, role,
                  root_task_id, retention_policy, visibility, created_at, updated_at
                )
                VALUES (?, 'wr_demo', ?, 'active', 'task', ?, ?, ?, 'until_closed', 'normal',
                        '2026-05-28T00:00:00Z', '2026-05-28T00:00:00Z')
                """,
                (task_id, title, process_level, role, task_id),
            )
            conn.execute(
                """
                INSERT INTO task_runs (
                  run_id, task_id, workroot_id, agent_name, status, goal, input_summary,
                  output_summary, source_lease_id, started_at
                )
                VALUES (?, ?, 'wr_demo', 'codex', 'active', ?, ?, ?, '', '2026-05-28T00:00:00Z')
                """,
                (run_id, task_id, run_goal or title, title, summary),
            )
            conn.execute(
                """
                INSERT INTO task_summaries (
                  summary_id, task_id, workroot_id, status, summary_text,
                  open_questions_json, next_actions_json, source_refs_json, generated_by, generated_at
                )
                VALUES (?, ?, 'wr_demo', 'current', ?, '[]', '[]', '[]', 'agent', '2026-05-28T00:00:00Z')
                """,
                (f"summary-{task_id}", task_id, summary),
            )
            if handoff_next_action:
                conn.execute(
                    """
                    INSERT INTO handoffs (
                      handoff_id, workroot_id, title, target, body, task_id, run_id, status,
                      current_state, next_action, created_at
                    )
                    VALUES (?, 'wr_demo', ?, 'task', ?, ?, ?, 'current', ?, ?, '2026-05-28T00:00:00Z')
                    """,
                    (
                        f"handoff-{task_id}",
                        f"Handoff {title}",
                        summary,
                        task_id,
                        run_id,
                        summary,
                        handoff_next_action,
                    ),
                )
            conn.commit()

    def insert_task_asset(self, *, task_id: str, asset_id: str, title: str, path: str) -> None:
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                INSERT INTO assets (
                  asset_id, workroot_id, asset_type, title, lifecycle_status,
                  publication_status, current_path, updatedAt
                )
                VALUES (?, 'wr_demo', 'markdown', ?, 'current', 'internal', ?, '2026-05-28T00:00:00Z')
                """,
                (asset_id, title, path),
            )
            conn.execute(
                """
                INSERT INTO relationship_nodes (
                  node_id, workroot_id, node_type, title, target_type, target_id
                )
                VALUES (?, 'wr_demo', 'task', ?, 'task', ?)
                """,
                (f"node-task-{task_id}", task_id, task_id),
            )
            conn.execute(
                """
                INSERT INTO relationship_nodes (
                  node_id, workroot_id, node_type, title, target_type, target_id
                )
                VALUES (?, 'wr_demo', 'asset', ?, 'asset', ?)
                """,
                (f"node-asset-{asset_id}", title, asset_id),
            )
            conn.execute(
                """
                INSERT INTO relationship_edges (
                  edge_id, workroot_id, from_node_id, to_node_id, relationship_type, confidence, status
                )
                VALUES (?, 'wr_demo', ?, ?, 'produced_asset', 1.0, 'active')
                """,
                (f"edge-task-{task_id}-asset-{asset_id}", f"node-task-{task_id}", f"node-asset-{asset_id}"),
            )
            conn.commit()

    def count_rows(self, table: str) -> int:
        with sqlite3.connect(self.sqlite_path) as conn:
            return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
