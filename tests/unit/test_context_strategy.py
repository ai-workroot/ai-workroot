from __future__ import annotations

import unittest

from ai_workroot.capabilities.context.strategy import (
    DisclosureLevel,
    FocusBoundary,
    LeaseFocusSignal,
    StrategyRequest,
    build_recall_plan,
)


class ContextStrategyTest(unittest.TestCase):
    def test_continue_work_signal_uses_l1_and_l2_without_l3(self) -> None:
        plan = build_recall_plan(
            StrategyRequest(
                query="Continue the founder operating plan.",
                mode="standard",
                focus=FocusBoundary(
                    workroot_id="wr_demo",
                    task_ref="task-1",
                    run_ref="run-1",
                    confidence="high",
                ),
                target_tokens=4000,
                hard_token_limit=6000,
                work_signal={
                    "phase": "orienting",
                    "work_kind": "continuation",
                    "intended_action": "inspect",
                    "focus": "Founder operating plan",
                },
            )
        )

        self.assertEqual(plan.intent, "continue_work")
        self.assertIn(DisclosureLevel.L1, plan.allowed_levels)
        self.assertIn(DisclosureLevel.L2, plan.allowed_levels)
        self.assertNotIn(DisclosureLevel.L3, plan.allowed_levels)
        self.assertTrue(all(source.level != DisclosureLevel.L3 for source in plan.sources))

    def test_query_language_alone_does_not_control_deep_recall(self) -> None:
        for query in (
            "Show evidence from the operating plan.",
            "source proof quote verify",
            "为什么当时这么决定？请给依据。",
            "根拠を見せてください。",
        ):
            with self.subTest(query=query):
                plan = build_recall_plan(
                    StrategyRequest(
                        query=query,
                        mode="standard",
                        focus=FocusBoundary(
                            workroot_id="wr_demo",
                            task_ref="task-1",
                            run_ref="run-1",
                            confidence="high",
                        ),
                        target_tokens=4000,
                        hard_token_limit=6000,
                    )
                )

                self.assertEqual(plan.intent, "orient")
                self.assertIn(DisclosureLevel.L1, plan.allowed_levels)
                self.assertIn(DisclosureLevel.L2, plan.allowed_levels)
                self.assertNotIn(DisclosureLevel.L3, plan.allowed_levels)
                self.assertFalse(any(source.name == "indexed_chunks" for source in plan.sources))

    def test_conservative_query_keeps_focus_but_broadens_shallow_search(self) -> None:
        plan = build_recall_plan(
            StrategyRequest(
                query="deleted sensitive detail",
                mode="standard",
                focus=FocusBoundary(
                    workroot_id="wr_demo",
                    task_ref="task-redaction",
                    run_ref="run-redaction",
                    confidence="high",
                ),
                target_tokens=4000,
                hard_token_limit=6000,
            )
        )

        self.assertEqual(plan.intent, "orient")
        self.assertEqual(plan.source_scope("current_task"), "task:task-redaction")
        self.assertEqual(plan.source_scope("context_recall_hints"), "workroot:current")
        self.assertEqual(plan.source_scope("context_candidates"), "workroot:current")
        self.assertNotIn(DisclosureLevel.L3, plan.allowed_levels)

    def test_evidence_signal_without_explicit_refs_uses_summary_refs_not_broad_l3(self) -> None:
        plan = build_recall_plan(
            StrategyRequest(
                query="继续昨天的定价策略，找一下我们当时为什么决定先不涨价。",
                mode="standard",
                focus=FocusBoundary(
                    workroot_id="wr_demo",
                    task_ref="task-1",
                    run_ref="run-1",
                    confidence="high",
                ),
                target_tokens=4000,
                hard_token_limit=6000,
                work_signal={
                    "phase": "orienting",
                    "work_kind": "continuation",
                    "intended_action": "inspect",
                    "focus": "定价策略：先不涨价的依据",
                    "concerns": ["needs_evidence"],
                },
            )
        )

        self.assertEqual(plan.intent, "evidence_lookup")
        self.assertNotIn(DisclosureLevel.L3, plan.allowed_levels)
        self.assertFalse(any(source.name == "indexed_chunks" for source in plan.sources))
        self.assertEqual(plan.evidence_decision.detail_mode, "summary_with_refs")
        self.assertEqual(plan.evidence_decision.reason, "explicit_ref_required")

    def test_explain_alias_marks_evidence_need_without_query_keyword_matching(self) -> None:
        plan = build_recall_plan(
            StrategyRequest(
                query="你刚才说下午可以做安静办公位，这个判断主要是从哪些现有信息看出来的？",
                mode="standard",
                focus=FocusBoundary(
                    workroot_id="wr_demo",
                    task_ref="task-1",
                    run_ref="run-1",
                    confidence="high",
                ),
                target_tokens=4000,
                hard_token_limit=6000,
                work_signal={
                    "phase": "deciding",
                    "work_kind": "continuation",
                    "intended_action": "explain",
                    "focus": "下午安静办公位判断依据",
                },
            )
        )

        self.assertEqual(plan.intent, "evidence_lookup")
        self.assertNotIn(DisclosureLevel.L3, plan.allowed_levels)
        self.assertFalse(any(source.name == "indexed_chunks" for source in plan.sources))
        self.assertTrue(plan.evidence_decision.requested)

    def test_same_work_signal_gives_same_plan_across_languages(self) -> None:
        plans = [
            build_recall_plan(
                StrategyRequest(
                    query=query,
                    mode="standard",
                    focus=FocusBoundary(workroot_id="wr_demo", task_ref="task-1", confidence="high"),
                    target_tokens=4000,
                    hard_token_limit=6000,
                    work_signal={
                        "phase": "orienting",
                        "work_kind": "continuation",
                        "intended_action": "inspect",
                        "focus": focus,
                        "concerns": ["needs_evidence"],
                    },
                )
            )
            for query, focus in (
                ("找一下当时的依据", "定价依据"),
                ("find the prior rationale", "pricing rationale"),
                ("短い確認", "pricing rationale"),
                ("unrelated compressed text", "pricing rationale"),
            )
        ]

        first = plans[0]
        for plan in plans[1:]:
            self.assertEqual(plan.intent, first.intent)
            self.assertEqual(plan.allowed_levels, first.allowed_levels)
            self.assertEqual([source.name for source in plan.sources], [source.name for source in first.sources])

    def test_refs_allow_scoped_l3_for_follow_up_without_evidence_words(self) -> None:
        plan = build_recall_plan(
            StrategyRequest(
                query="展开刚才那个决定",
                mode="standard",
                focus=FocusBoundary(workroot_id="wr_demo", task_ref="task-1", confidence="high"),
                target_tokens=4000,
                hard_token_limit=6000,
                work_signal={
                    "phase": "orienting",
                    "work_kind": "continuation",
                    "intended_action": "inspect",
                    "focus": "刚才那个决定",
                    "concerns": [],
                    "refs": ["decision:dec_001"],
                },
            )
        )

        self.assertEqual(plan.intent, "inspect")
        self.assertIn(DisclosureLevel.L3, plan.allowed_levels)
        self.assertTrue(any(source.name == "ref_indexed_chunks" for source in plan.sources))
        self.assertEqual(plan.evidence_decision.detail_mode, "ref_scoped_evidence")

    def test_needs_evidence_with_explicit_refs_uses_ref_scoped_evidence(self) -> None:
        plan = build_recall_plan(
            StrategyRequest(
                query="展开这个依据",
                mode="standard",
                focus=FocusBoundary(workroot_id="wr_demo", task_ref="task-1", confidence="high"),
                target_tokens=4000,
                hard_token_limit=6000,
                work_signal={
                    "phase": "orienting",
                    "work_kind": "continuation",
                    "intended_action": "inspect",
                    "focus": "定价依据",
                    "concerns": ["needs_evidence"],
                    "refs": ["asset:asset_001"],
                },
            )
        )

        self.assertEqual(plan.intent, "evidence_lookup")
        self.assertIn(DisclosureLevel.L3, plan.allowed_levels)
        self.assertTrue(any(source.name == "ref_indexed_chunks" for source in plan.sources))
        self.assertFalse(any(source.name == "indexed_chunks" for source in plan.sources))
        self.assertEqual(plan.evidence_decision.detail_mode, "ref_scoped_evidence")
        self.assertEqual(plan.evidence_decision.refs, ("asset:asset_001",))

    def test_asset_edit_signal_allows_scoped_l3(self) -> None:
        plan = build_recall_plan(
            StrategyRequest(
                query="更新运营简报，把最新决定补进去",
                mode="standard",
                focus=FocusBoundary(workroot_id="wr_demo", task_ref="task-1", confidence="high"),
                target_tokens=4000,
                hard_token_limit=6000,
                work_signal={
                    "phase": "executing",
                    "work_kind": "authoring",
                    "intended_action": "edit",
                    "focus": "运营简报",
                    "concerns": ["may_change_user_assets"],
                    "refs": ["asset:asset_001"],
                },
            )
        )

        self.assertEqual(plan.intent, "edit_asset")
        self.assertIn(DisclosureLevel.L3, plan.allowed_levels)

    def test_needs_evidence_without_scope_does_not_allow_broad_l3(self) -> None:
        plan = build_recall_plan(
            StrategyRequest(
                query="为什么",
                mode="standard",
                focus=FocusBoundary(workroot_id="wr_demo", confidence="low", reason="ambiguous"),
                target_tokens=4000,
                hard_token_limit=6000,
                work_signal={
                    "phase": "orienting",
                    "work_kind": "continuation",
                    "intended_action": "inspect",
                    "focus": "为什么",
                    "concerns": ["needs_evidence"],
                },
            )
        )

        self.assertEqual(plan.intent, "evidence_lookup")
        self.assertNotIn(DisclosureLevel.L3, plan.allowed_levels)
        self.assertEqual(plan.evidence_decision.detail_mode, "summary_with_refs")

    def test_low_focus_confidence_stays_shallow(self) -> None:
        plan = build_recall_plan(
            StrategyRequest(
                query="Continue.",
                mode="standard",
                focus=FocusBoundary(workroot_id="wr_demo", confidence="low", reason="ambiguous"),
                target_tokens=4000,
                hard_token_limit=6000,
            )
        )

        self.assertEqual(plan.intent, "unknown")
        self.assertEqual({source.level for source in plan.sources}, {DisclosureLevel.L1})

    def test_low_focus_specific_query_without_work_signal_stays_shallow(self) -> None:
        plan = build_recall_plan(
            StrategyRequest(
                query="needle",
                mode="standard",
                focus=FocusBoundary(workroot_id="wr_demo", confidence="none", reason="no active task"),
                target_tokens=4000,
                hard_token_limit=6000,
            )
        )

        self.assertEqual(plan.intent, "unknown")
        self.assertEqual(plan.allowed_levels, (DisclosureLevel.L1,))
        self.assertEqual(plan.source_limit("indexed_chunks"), 0)

    def test_deep_mode_without_evidence_words_does_not_force_l3(self) -> None:
        plan = build_recall_plan(
            StrategyRequest(
                query="Continue the current strategy.",
                mode="deep",
                focus=FocusBoundary(workroot_id="wr_demo", task_ref="task-1", confidence="high"),
                target_tokens=4000,
                hard_token_limit=6000,
            )
        )

        self.assertEqual(plan.intent, "orient")
        self.assertNotIn(DisclosureLevel.L3, plan.allowed_levels)

    def test_work_signal_continue_preserve_is_not_overridden_by_query_keywords(self) -> None:
        plan = build_recall_plan(
            StrategyRequest(
                query="evidence source verify quote search",
                mode="standard",
                focus=FocusBoundary(workroot_id="wr_demo", task_ref="task-1", confidence="high"),
                target_tokens=4000,
                hard_token_limit=6000,
                work_signal={
                    "phase": "preserving",
                    "work_kind": "continuation",
                    "intended_action": "preserve",
                    "focus": "Current checkpoint",
                },
            )
        )

        self.assertEqual(plan.intent, "continue_work")
        self.assertIn(DisclosureLevel.L2, plan.allowed_levels)
        self.assertNotIn(DisclosureLevel.L3, plan.allowed_levels)

    def test_query_evidence_keywords_without_protocol_scope_are_conservative(self) -> None:
        plan = build_recall_plan(
            StrategyRequest(
                query="evidence source verify quote",
                mode="standard",
                focus=FocusBoundary(workroot_id="wr_demo", confidence="none", reason="ambiguous"),
                target_tokens=4000,
                hard_token_limit=6000,
            )
        )

        self.assertEqual(plan.intent, "unknown")
        self.assertNotIn(DisclosureLevel.L3, plan.allowed_levels)

    def test_state_conflict_lease_blocks_l3_for_unscoped_evidence(self) -> None:
        plan = build_recall_plan(
            StrategyRequest(
                query="Show evidence from the operating plan.",
                mode="standard",
                focus=FocusBoundary(workroot_id="wr_demo", task_ref="task-1", confidence="high"),
                target_tokens=4000,
                hard_token_limit=6000,
                work_signal={
                    "phase": "orienting",
                    "work_kind": "continuation",
                    "intended_action": "inspect",
                    "focus": "Founder operating plan evidence",
                    "concerns": ["needs_evidence"],
                },
                lease_signal=LeaseFocusSignal(status="state_conflict", freshness="stale"),
            )
        )

        self.assertEqual(plan.intent, "evidence_lookup")
        self.assertNotIn(DisclosureLevel.L3, plan.allowed_levels)
        self.assertFalse(any(source.name == "indexed_chunks" for source in plan.sources))
        self.assertEqual(plan.trace_payload()["leaseSignal"]["status"], "state_conflict")
        self.assertEqual(plan.evidence_decision.reason, "explicit_ref_required")

    def test_interrupted_lease_keeps_recovery_shallow(self) -> None:
        plan = build_recall_plan(
            StrategyRequest(
                query="I am back. Continue.",
                mode="standard",
                focus=FocusBoundary(workroot_id="wr_demo", task_ref="task-1", confidence="high"),
                target_tokens=4000,
                hard_token_limit=6000,
                work_signal={
                    "phase": "orienting",
                    "work_kind": "continuation",
                    "intended_action": "inspect",
                    "focus": "Current work",
                },
                lease_signal=LeaseFocusSignal(status="interrupted", freshness="fresh"),
            )
        )

        self.assertEqual(plan.intent, "continue_work")
        self.assertIn(DisclosureLevel.L2, plan.allowed_levels)
        self.assertNotIn(DisclosureLevel.L3, plan.allowed_levels)
        self.assertIn("lease:interrupted", plan.debug_reasons)

    def test_fresh_active_lease_still_requires_explicit_refs_for_evidence_chunks(self) -> None:
        plan = build_recall_plan(
            StrategyRequest(
                query="Show evidence from the operating plan.",
                mode="standard",
                focus=FocusBoundary(workroot_id="wr_demo", task_ref="task-1", confidence="medium"),
                target_tokens=4000,
                hard_token_limit=6000,
                work_signal={
                    "phase": "orienting",
                    "work_kind": "continuation",
                    "intended_action": "inspect",
                    "focus": "Founder operating plan evidence",
                    "concerns": ["needs_evidence"],
                },
                lease_signal=LeaseFocusSignal(status="fresh_active", freshness="fresh"),
            )
        )

        self.assertNotIn(DisclosureLevel.L3, plan.allowed_levels)
        self.assertFalse(any(source.name == "indexed_chunks" for source in plan.sources))
        self.assertEqual(plan.trace_payload()["leaseSignal"]["status"], "fresh_active")

    def test_interrupted_lease_allows_explicit_ref_evidence_only(self) -> None:
        plan = build_recall_plan(
            StrategyRequest(
                query="Show evidence from this plan.",
                mode="standard",
                focus=FocusBoundary(workroot_id="wr_demo", task_ref="task-1", confidence="high"),
                target_tokens=4000,
                hard_token_limit=6000,
                work_signal={
                    "phase": "orienting",
                    "work_kind": "continuation",
                    "intended_action": "inspect",
                    "focus": "Plan evidence",
                    "concerns": ["needs_evidence"],
                    "refs": ["asset:asset-plan"],
                },
                lease_signal=LeaseFocusSignal(status="interrupted", freshness="fresh"),
            )
        )

        self.assertIn(DisclosureLevel.L3, plan.allowed_levels)
        self.assertTrue(any(source.name == "ref_indexed_chunks" for source in plan.sources))
        self.assertFalse(any(source.name == "indexed_chunks" for source in plan.sources))
        self.assertEqual(plan.evidence_decision.detail_mode, "ref_scoped_evidence")


if __name__ == "__main__":
    unittest.main()
