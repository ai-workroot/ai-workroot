from __future__ import annotations

import json
import unittest

from ai_workroot.protocol.packet import build_private_packet, render_private_packet_markdown


class ProtocolPacketTest(unittest.TestCase):
    def test_new_work_packet_maps_start_work_call(self) -> None:
        response = {
            "agent_may_continue": True,
            "workroot_view": {
                "focus": "new_work",
                "confidence": "high",
                "task_brief": "Redesign Agent protocol interaction",
                "current_state": "",
                "next_action": "",
                "open_items": [],
                "recent_done_items": [],
                "warnings": [],
            },
            "workroot_contract": {
                "next_exchange": {"action": "commit", "reason": "start_work", "required": False},
                "commit_contract": {
                    "lease_id": "lease-1",
                    "accepted_shapes": ["start_work"],
                    "required_before_stop": [],
                },
                "state_refs": {"task_ref": None, "run_ref": None},
                "debug": {"effects": [{"type": "internal", "target_type": "debug", "target_id": "x"}]},
            },
            "result": {"accepted": False, "status": "not_recorded", "warnings": []},
        }

        packet = build_private_packet(response, adapter="cli", agent="codex")

        self.assertEqual(packet["v"], "workroot.packet.v1")
        self.assertIn("private_do_not_show_user", packet["rules"])
        self.assertEqual(packet["work"]["focus"], "new_work")
        self.assertEqual(packet["work"]["summary"], "Redesign Agent protocol interaction")
        self.assertEqual(packet["call"]["action"], "commit")
        self.assertEqual(packet["call"]["shape"], "start_work")
        self.assertEqual(packet["call"]["when"], "now")
        self.assertEqual(packet["call"]["fields"], ["title", "summary", "persistence"])
        self.assertEqual(packet["call"]["optional"], ["parent_task_id"])
        self.assertEqual(packet["refs"], {"exchange": "lease-1"})
        self.assertEqual(packet["write"]["status"], "not_recorded")
        self.assertEqual(packet["write"]["meaning"], "No durable fact was written.")
        self.assertNotIn("warnings", packet["write"])
        self.assertIn("--lease lease-1", packet["adapter_hint"]["cli"])
        self.assertIn("--shape start-work", packet["adapter_hint"]["cli"])
        self.assertIn("--parent-task-id", packet["adapter_hint"]["cli"])
        self.assertNotIn("parent-task-ref", packet["adapter_hint"]["cli"])
        self.assertNotIn("parent_task_ref", json.dumps(packet, ensure_ascii=False))
        self.assertNotIn("quick", packet["adapter_hint"]["cli"])
        serialized = json.dumps(packet, ensure_ascii=False)
        self.assertNotIn("debug", serialized)
        self.assertNotIn("effects", serialized)

    def test_start_work_packet_uses_temporary_persistence_when_contract_requires_inbox(self) -> None:
        response = {
            "agent_may_continue": True,
            "workroot_view": {
                "focus": "new_work",
                "confidence": "high",
                "task_brief": "Loose sponsor idea",
            },
            "workroot_contract": {
                "next_exchange": {"action": "commit", "reason": "start_work", "required": False},
                "commit_contract": {
                    "lease_id": "lease-inbox",
                    "accepted_shapes": ["start_work"],
                    "required_before_stop": [],
                    "write_policy": {
                        "expected_start_work_persistence": "temporary",
                        "expected_task_role": "inbox",
                        "source": "work_signal",
                    },
                },
                "state_refs": {"task_ref": None, "run_ref": None},
            },
            "result": {"accepted": False, "status": "not_recorded", "warnings": []},
        }

        packet = build_private_packet(response, adapter="cli", agent="codex")
        rendered = render_private_packet_markdown(response, adapter="cli", agent="codex")

        self.assertEqual(packet["call"]["write_policy"]["expected_start_work_persistence"], "temporary")
        self.assertIn("--persistence temporary", packet["call"]["command"])
        self.assertNotIn("--persistence <normal|temporary>", packet["call"]["command"])
        self.assertIn('Use work_kind="inbox" for side, loose, temporary, or uncertain-boundary work.', rendered)

    def test_checkpoint_packet_limits_open_and_done_items(self) -> None:
        response = {
            "agent_may_continue": True,
            "workroot_view": {
                "focus": "continuation",
                "confidence": "high",
                "task_brief": "Protocol packet design",
                "current_state": "Core fields agreed.",
                "next_action": "Implement packet renderer.",
                "open_items": [
                    {"title": "Open 1"},
                    {"title": "Open 2"},
                    {"title": "Open 3"},
                    {"title": "Open 4"},
                ],
                "recent_done_items": [
                    {"title": "Done 1", "result_summary": "A"},
                    {"title": "Done 2", "result_summary": "B"},
                    {"title": "Done 3", "result_summary": "C"},
                    {"title": "Done 4", "result_summary": "D"},
                ],
                "warnings": [],
            },
            "workroot_contract": {
                "next_exchange": {"action": "commit", "reason": "meaningful_checkpoint", "required": False},
                "commit_contract": {
                    "lease_id": "lease-2",
                    "accepted_shapes": ["checkpoint", "continuation_checkpoint", "state_update"],
                    "required_before_stop": [],
                },
                "state_refs": {"task_ref": "task-1", "run_ref": "run-1"},
            },
            "result": {"accepted": True, "status": "applied", "warnings": []},
        }

        packet = build_private_packet(response, adapter="cli", agent="codex")

        self.assertEqual(packet["work"]["open"], ["Open 1", "Open 2", "Open 3"])
        self.assertEqual(packet["work"]["done"], ["Done 1: A", "Done 2: B", "Done 3: C"])
        self.assertEqual(packet["call"]["shape"], "checkpoint")
        self.assertEqual(packet["call"]["when"], "at_checkpoint")
        self.assertEqual(packet["call"]["also"], ["asset_if_created", "decision_if_made"])
        self.assertEqual(packet["refs"], {"exchange": "lease-2", "task": "task-1", "run": "run-1"})
        self.assertEqual(packet["write"]["meaning"], "Previous Workroot fact was saved.")

    def test_packet_call_includes_copyable_command_and_markdown_preface(self) -> None:
        response = {
            "agent_may_continue": True,
            "workroot_view": {
                "focus": "continuation",
                "confidence": "high",
                "task_brief": "Protocol packet design",
                "current_state": "Core fields agreed.",
                "next_action": "Implement packet renderer.",
                "open_items": [],
                "recent_done_items": [],
                "warnings": [],
            },
            "workroot_contract": {
                "next_exchange": {"action": "commit", "reason": "meaningful_checkpoint", "required": False},
                "commit_contract": {
                    "lease_id": "lease-copyable",
                    "accepted_shapes": ["checkpoint", "continuation"],
                    "required_before_stop": [],
                },
                "state_refs": {"task_ref": "task-1", "run_ref": "run-1"},
            },
            "result": {"accepted": True, "status": "applied", "warnings": []},
        }

        packet = build_private_packet(response, adapter="cli", agent="codex")
        rendered = render_private_packet_markdown(response, adapter="cli", agent="codex")

        self.assertIn("command", packet["call"])
        self.assertIn("workroot agent commit", packet["call"]["command"])
        self.assertIn("--format packet", packet["call"]["command"])
        self.assertIn("--shape checkpoint", packet["call"]["command"])
        self.assertIn("--lease lease-copyable", packet["call"]["command"])
        self.assertIn("--cwd .", packet["call"]["command"])
        self.assertIn("Meaning:", rendered)
        self.assertIn("Exact next call:", rendered)
        self.assertIn(packet["call"]["command"], rendered)

    def test_packet_prefers_continuation_when_required_before_stop(self) -> None:
        response = {
            "agent_may_continue": True,
            "workroot_view": {
                "focus": "continuation",
                "confidence": "high",
                "task_brief": "家政培训门店月度经营方向梳理",
                "current_state": "本轮已完成复盘表和检查清单。",
                "next_action": "下次先检查补练验收、收费边界和活动线索。",
                "open_items": [],
                "recent_done_items": [],
                "warnings": [],
            },
            "workroot_contract": {
                "next_exchange": {"action": "commit", "reason": "meaningful_checkpoint", "required": False},
                "commit_contract": {
                    "lease_id": "lease-stop",
                    "accepted_shapes": ["checkpoint", "continuation", "asset"],
                    "required_before_stop": ["continuation"],
                },
                "state_refs": {"task_ref": "task-service-month", "run_ref": "run-service-month"},
            },
            "result": {"accepted": True, "status": "applied", "warnings": []},
        }

        packet = build_private_packet(response, adapter="cli", agent="codex")
        rendered = render_private_packet_markdown(response, adapter="cli", agent="codex")

        self.assertEqual(packet["call"]["shape"], "continuation")
        self.assertEqual(packet["call"]["fields"], ["state", "next"])
        self.assertIn("--shape continuation", packet["call"]["command"])
        self.assertIn("--state", packet["call"]["command"])
        self.assertIn("--next", packet["call"]["command"])
        self.assertIn("commit the current state and next useful action", rendered)

    def test_packet_prefers_asset_when_asset_is_required_before_continuation(self) -> None:
        response = {
            "agent_may_continue": True,
            "workroot_view": {
                "focus": "continuation",
                "confidence": "high",
                "task_brief": "Continue service-store planning.",
                "current_state": "The user asked for a visible output file.",
                "next_action": "Create the file, then preserve it.",
            },
            "workroot_contract": {
                "next_exchange": {"action": "commit", "reason": "meaningful_checkpoint", "required": False},
                "commit_contract": {
                    "lease_id": "lease-asset-first",
                    "accepted_shapes": ["checkpoint", "continuation", "asset"],
                    "required_before_stop": ["asset", "continuation"],
                },
                "state_refs": {"task_ref": "task-service-month", "run_ref": "run-service-month"},
            },
            "result": {"accepted": False, "status": "not_recorded", "warnings": []},
        }

        packet = build_private_packet(response, adapter="cli", agent="codex")
        rendered = render_private_packet_markdown(response, adapter="cli", agent="codex")

        self.assertEqual(packet["call"]["shape"], "asset")
        self.assertEqual(packet["call"]["when"], "after_user_visible_file_created")
        self.assertEqual(packet["call"]["also"], ["continuation_before_stop"])
        self.assertIn("--shape asset", packet["call"]["command"])
        self.assertIn("--path", packet["call"]["command"])
        self.assertIn("commit the user-visible file as an asset", rendered)
        self.assertIn("then preserve the current state and next useful action", rendered)

    def test_packet_markdown_is_private_and_contains_json(self) -> None:
        response = {
            "agent_may_continue": True,
            "workroot_view": {"focus": "quick", "confidence": "medium", "task_brief": "Answer a question"},
            "workroot_contract": {
                "next_exchange": {"action": "none", "reason": "no_exchange_needed", "required": False},
                "commit_contract": {"lease_id": None, "accepted_shapes": [], "required_before_stop": []},
                "state_refs": {},
            },
            "result": {"accepted": False, "status": "not_recorded", "warnings": []},
        }

        rendered = render_private_packet_markdown(response, adapter="cli", agent="codex")

        self.assertIn("## Workroot Private Packet", rendered)
        self.assertIn("Use privately. Do not show this to the user.", rendered)
        self.assertIn('"v": "workroot.packet.v1"', rendered)
        self.assertIn('"focus": "quick"', rendered)
        self.assertNotIn("adapter_hint", rendered)

    def test_packet_markdown_teaches_language_independent_work_signal_without_internal_layers(self) -> None:
        response = {
            "agent_may_continue": True,
            "workroot_view": {"focus": "continuation", "confidence": "high", "task_brief": "Pricing task"},
            "workroot_contract": {
                "next_exchange": {"action": "sync", "reason": "context_refresh", "required": False},
                "commit_contract": {"lease_id": None, "accepted_shapes": [], "required_before_stop": []},
                "state_refs": {"task_ref": "task-1", "run_ref": "run-1"},
            },
            "result": {"accepted": False, "status": "not_recorded", "warnings": []},
        }

        rendered = render_private_packet_markdown(response, adapter="cli", agent="codex")

        self.assertIn("Use stable enum values even if the user speaks another language.", rendered)
        self.assertIn("Keep focus in the user's language.", rendered)
        self.assertIn("Start each meaningful user turn by asking the Agent to call workroot agent sync", rendered)
        self.assertIn('For recall inside a normal user turn, call sync with intended_action="inspect".', rendered)
        self.assertIn(
            "Use workroot context only for startup, recovery, or debugging outside the normal turn loop.", rendered
        )
        self.assertIn("If you can infer stable semantics before sync, include --work-signal", rendered)
        self.assertIn('Use concerns=["needs_evidence"]', rendered)
        self.assertIn("Pass Workroot refs back in work_signal.refs", rendered)
        self.assertIn("Workroot decides what context to retrieve and how much detail to include.", rendered)
        self.assertNotIn("Start each meaningful user turn by asking the Agent to call workroot context", rendered)
        self.assertNotIn("L1", rendered)
        self.assertNotIn("L2", rendered)
        self.assertNotIn("L3", rendered)

    def test_sync_packet_includes_adapter_hint_without_shape(self) -> None:
        response = {
            "agent_may_continue": True,
            "workroot_view": {
                "focus": "continuation",
                "confidence": "medium",
                "task_brief": "Resume protocol work",
            },
            "workroot_contract": {
                "next_exchange": {"action": "sync", "reason": "before_work", "required": False},
                "commit_contract": {"lease_id": None, "accepted_shapes": [], "required_before_stop": []},
                "state_refs": {},
            },
            "result": {"accepted": False, "status": "not_recorded", "warnings": []},
        }

        packet = build_private_packet(response, adapter="cli", agent="codex")

        self.assertEqual(packet["call"]["action"], "sync")
        self.assertEqual(packet["call"]["when"], "if_durable_persistence_is_still_relevant")
        self.assertNotIn("shape", packet["call"])
        self.assertIn("adapter_hint", packet)
        self.assertIn(
            "workroot agent sync --agent codex --transport cli --cwd . --reason before_work "
            '--format packet --query "<current user request or short intent>"',
            packet["adapter_hint"]["cli"],
        )
        self.assertIn("--format packet", packet["adapter_hint"]["cli"])
        self.assertIn("--work-signal", packet["adapter_hint"]["cli"])
        self.assertEqual(
            packet["call"]["work_signal"],
            {
                "phase": "planning",
                "work_kind": "task",
                "intended_action": "plan",
                "focus": "current user request or short intent",
            },
        )

    def test_sync_packet_adapter_hint_maps_internal_exchange_reason_to_valid_cli_reason(self) -> None:
        response = {
            "agent_may_continue": True,
            "workroot_view": {
                "focus": "new_work",
                "confidence": "medium",
                "task_brief": "Start durable work after startup context",
            },
            "workroot_contract": {
                "next_exchange": {"action": "sync", "reason": "alignment_required", "required": False},
                "commit_contract": {"lease_id": None, "accepted_shapes": [], "required_before_stop": []},
                "state_refs": {},
            },
            "result": {"accepted": False, "status": "not_recorded", "warnings": []},
        }

        packet = build_private_packet(response, adapter="cli", agent="codex")

        self.assertIn(
            "workroot agent sync --agent codex --transport cli --cwd . --reason before_work "
            '--format packet --query "<current user request or short intent>"',
            packet["adapter_hint"]["cli"],
        )
        self.assertIn("--format packet", packet["adapter_hint"]["cli"])
        self.assertIn("--work-signal", packet["adapter_hint"]["cli"])
        self.assertNotIn("alignment_required", packet["adapter_hint"]["cli"])

    def test_sync_packet_does_not_render_placeholder_as_exact_next_call(self) -> None:
        response = {
            "agent_may_continue": True,
            "workroot_view": {
                "focus": "continuation",
                "confidence": "medium",
                "task_brief": "Resume protocol work",
            },
            "workroot_contract": {
                "next_exchange": {"action": "sync", "reason": "before_work", "required": False},
                "commit_contract": {"lease_id": None, "accepted_shapes": [], "required_before_stop": []},
                "state_refs": {},
            },
            "result": {"accepted": False, "status": "not_recorded", "warnings": []},
        }

        rendered = render_private_packet_markdown(response, adapter="cli", agent="codex")

        exact_section = rendered.split("JSON:", 1)[0]
        self.assertNotIn("Exact next call:\nworkroot agent sync", exact_section)
        self.assertNotIn('--query "<short intent>"', exact_section)
        self.assertIn("Call template:", exact_section)

    def test_read_only_context_packet_does_not_imply_direct_commit_is_available(self) -> None:
        response = {
            "agent_may_continue": True,
            "workroot_view": {
                "focus": "ambiguous",
                "confidence": "low",
                "task_brief": "Continue visible work while focus is unclear.",
            },
            "workroot_contract": {
                "exchange_mode": "read_only",
                "next_exchange": {"action": "none", "reason": "no_exchange_needed", "required": False},
                "commit_contract": {
                    "lease_id": None,
                    "accepted_shapes": [],
                    "required_before_stop": [],
                },
                "state_refs": {},
            },
            "result": {"accepted": False, "status": "not_recorded", "warnings": []},
        }

        packet = build_private_packet(response, adapter="cli", agent="codex")
        rendered = render_private_packet_markdown(response, adapter="cli", agent="codex")

        self.assertTrue(packet["call"]["read_only"])
        self.assertEqual(packet["call"]["action"], "none")
        self.assertIn("read-only context does not grant a lease", rendered.lower())
        self.assertIn("sync first", rendered.lower())
        self.assertNotIn("L1", rendered)
        self.assertNotIn("L2", rendered)
        self.assertNotIn("L3", rendered)

    def test_ambiguous_sync_packet_exposes_candidates_without_selected_ref_command(self) -> None:
        response = {
            "agent_may_continue": True,
            "workroot_view": {
                "focus": "ambiguous",
                "confidence": "low",
                "task_brief": "Multiple possible tasks can continue.",
            },
            "workroot_contract": {
                "next_exchange": {
                    "action": "sync",
                    "reason": "focus_refinement_required",
                    "required": False,
                },
                "commit_contract": {
                    "lease_id": None,
                    "accepted_shapes": [],
                    "required_before_stop": [],
                },
                "state_refs": {"task_ref": None, "run_ref": None},
                "context_refs": [
                    {
                        "ref": "task:task-one",
                        "run_ref": "run-one",
                        "title": "One",
                        "summary": "First task.",
                    },
                    {
                        "ref": "task:task-two",
                        "run_ref": "run-two",
                        "title": "Two",
                        "summary": "Second task.",
                    },
                ],
            },
            "result": {"accepted": False, "status": "not_recorded", "warnings": []},
        }

        packet = build_private_packet(response, adapter="cli", agent="codex")
        rendered = render_private_packet_markdown(response, adapter="cli", agent="codex")

        self.assertEqual(packet["call"]["action"], "sync")
        self.assertNotIn("refs", packet["call"]["work_signal"])
        self.assertEqual(
            [item["ref"] for item in packet["refs"]["candidates"]],
            ["task:task-one", "task:task-two"],
        )
        self.assertNotIn("task:task-one", packet["call"]["command_template"])
        self.assertNotIn("task:task-two", packet["call"]["command_template"])
        self.assertIn("choose the relevant ref", rendered.lower())
        self.assertNotIn("L1", rendered)
        self.assertNotIn("L2", rendered)
        self.assertNotIn("L3", rendered)

    def test_sync_packet_includes_known_state_when_task_and_run_refs_are_known(self) -> None:
        response = {
            "agent_may_continue": True,
            "workroot_view": {
                "focus": "continuation",
                "confidence": "high",
                "task_brief": "Continue task.",
            },
            "workroot_contract": {
                "next_exchange": {"action": "sync", "reason": "resync_required", "required": False},
                "commit_contract": {
                    "lease_id": None,
                    "accepted_shapes": [],
                    "required_before_stop": [],
                },
                "state_refs": {"task_ref": "task-1", "run_ref": "run-1"},
            },
            "result": {"accepted": False, "status": "rejected", "warnings": ["missing_exchange_lease_id"]},
        }

        packet = build_private_packet(response, adapter="cli", agent="codex")

        self.assertEqual(packet["refs"], {"task": "task-1", "run": "run-1"})
        self.assertEqual(packet["call"]["known_state"], {"task_id": "task-1", "run_id": "run-1"})
        self.assertIn("--known-state", packet["call"]["command_template"])
        self.assertIn('"task_id":"task-1"', packet["call"]["command_template"])
        self.assertIn("--known-state", packet["adapter_hint"]["cli"])

    def test_state_update_packet_omits_empty_optional_fields(self) -> None:
        response = {
            "agent_may_continue": True,
            "workroot_view": {
                "focus": "continuation",
                "confidence": "high",
                "task_brief": "Update protocol state",
            },
            "workroot_contract": {
                "next_exchange": {"action": "commit", "reason": "state_sync", "required": False},
                "commit_contract": {
                    "lease_id": "lease-3",
                    "accepted_shapes": ["state_update"],
                    "required_before_stop": [],
                },
                "state_refs": {"task_ref": "task-2", "run_ref": "run-2"},
            },
            "result": {"accepted": False, "status": "not_recorded", "warnings": []},
        }

        packet = build_private_packet(response, adapter="cli", agent="codex")

        self.assertEqual(packet["call"]["shape"], "state_update")
        self.assertEqual(packet["call"]["when"], "at_checkpoint")
        self.assertEqual(packet["call"]["fields"], ["target", "change"])
        self.assertNotIn("optional", packet["call"])
        self.assertIn("adapter_hint", packet)
        self.assertIn("--lease lease-3", packet["adapter_hint"]["cli"])
        self.assertIn("--shape state-update", packet["adapter_hint"]["cli"])

    def test_asset_packet_hint_uses_asset_kind_and_lease(self) -> None:
        response = {
            "agent_may_continue": True,
            "workroot_view": {"focus": "continuation", "confidence": "high", "task_brief": "Capture asset"},
            "workroot_contract": {
                "next_exchange": {"action": "commit", "reason": "asset_ready", "required": False},
                "commit_contract": {
                    "lease_id": "lease-asset",
                    "accepted_shapes": ["asset"],
                    "required_before_stop": [],
                },
                "state_refs": {"task_ref": "task-1", "run_ref": "run-1"},
            },
            "result": {"accepted": False, "status": "not_recorded", "warnings": []},
        }

        packet = build_private_packet(response, adapter="cli", agent="codex")

        self.assertEqual(packet["call"]["fields"], ["title", "asset_kind", "path", "summary", "status"])
        self.assertIn("--lease lease-asset", packet["adapter_hint"]["cli"])
        self.assertIn("--asset-kind", packet["adapter_hint"]["cli"])
        self.assertNotIn("--kind", packet["adapter_hint"]["cli"])

    def test_private_packet_can_include_compact_output_rule_guidance(self) -> None:
        response = {
            "workroot_view": {
                "focus": "continuation",
                "task_brief": "Continue work.",
                "output_rules": [{"asset_kind": "*", "path": "workroot-output", "role": "default_output"}],
            },
            "workroot_contract": {
                "next_exchange": {"action": "commit", "reason": "asset_ready", "required": False},
                "commit_contract": {
                    "lease_id": "lease-output",
                    "accepted_shapes": ["asset"],
                    "required_before_stop": [],
                },
                "state_refs": {},
            },
            "result": {"accepted": True, "status": "applied"},
        }

        packet = build_private_packet(response)

        self.assertEqual(packet["output"]["default_path"], "workroot-output")
        self.assertEqual(packet["output"]["asset_path_required"], True)

    def test_decision_packet_hint_uses_reason_text_and_lease(self) -> None:
        response = {
            "agent_may_continue": True,
            "workroot_view": {"focus": "decision", "confidence": "high", "task_brief": "Capture decision"},
            "workroot_contract": {
                "next_exchange": {"action": "commit", "reason": "decision_ready", "required": False},
                "commit_contract": {
                    "lease_id": "lease-decision",
                    "accepted_shapes": ["decision"],
                    "required_before_stop": [],
                },
                "state_refs": {"task_ref": "task-1", "run_ref": "run-1"},
            },
            "result": {"accepted": False, "status": "not_recorded", "warnings": []},
        }

        packet = build_private_packet(response, adapter="cli", agent="codex")

        self.assertEqual(packet["call"]["fields"], ["title", "decision", "reason_text", "scope"])
        self.assertIn("--lease lease-decision", packet["adapter_hint"]["cli"])
        self.assertIn("--reason-text", packet["adapter_hint"]["cli"])
        self.assertNotIn("--reason <", packet["adapter_hint"]["cli"])

    def test_packet_prefers_shape_specific_contract_when_available(self) -> None:
        response = {
            "agent_may_continue": True,
            "workroot_view": {"focus": "decision", "confidence": "high", "task_brief": "Capture decision"},
            "workroot_contract": {
                "next_exchange": {"action": "commit", "reason": "decision_ready", "required": False},
                "commit_contract": {
                    "lease_id": "lease-decision",
                    "accepted_shapes": ["decision"],
                    "required_before_stop": [],
                    "shape_contracts": {
                        "decision": {
                            "required": ["title", "decision", "reason_text"],
                            "optional": ["scope"],
                            "not_accepted": ["summary"],
                            "capture_rule": "stable_decisions_only",
                            "command_template": (
                                "workroot agent commit --format packet --shape decision --lease lease-decision "
                                '--title "<decision title>" --decision "<decision>" '
                                '--reason-text "<reason>" --scope <scope> --cwd .'
                            ),
                        }
                    },
                },
                "state_refs": {"task_ref": "task-1", "run_ref": "run-1"},
            },
            "result": {"accepted": False, "status": "not_recorded", "warnings": []},
        }

        packet = build_private_packet(response, adapter="cli", agent="codex")

        self.assertEqual(packet["call"]["fields"], ["title", "decision", "reason_text"])
        self.assertEqual(packet["call"]["optional"], ["scope"])
        self.assertEqual(packet["call"]["not_accepted"], ["summary"])
        self.assertEqual(
            packet["call"]["command"],
            response["workroot_contract"]["commit_contract"]["shape_contracts"]["decision"]["command_template"],
        )

    def test_write_meanings_are_natural_language_and_empty_warnings_are_omitted(self) -> None:
        cases = [
            (True, "applied", "Previous Workroot fact was saved."),
            (False, "not_recorded", "No durable fact was written."),
            (False, "resync_required", "Sync again before retrying persistence."),
            (
                False,
                "quarantined",
                "Workroot recorded the attempt but did not project it into durable continuity.",
            ),
            (False, "rejected", "Workroot rejected the write. Continue user work and sync before retrying."),
            (False, "unknown", "Continue helping the user."),
        ]
        for accepted, status, meaning in cases:
            with self.subTest(status=status):
                response = {
                    "agent_may_continue": True,
                    "workroot_view": {"focus": "quick", "confidence": "medium", "task_brief": "Answer"},
                    "workroot_contract": {
                        "next_exchange": {"action": "none", "reason": "no_exchange_needed", "required": False},
                        "commit_contract": {"lease_id": None, "accepted_shapes": [], "required_before_stop": []},
                        "state_refs": {},
                    },
                    "result": {"accepted": accepted, "status": status, "warnings": []},
                }

                packet = build_private_packet(response, adapter="cli", agent="codex")

                self.assertEqual(packet["write"]["meaning"], meaning)
                self.assertNotIn("warnings", packet["write"])

    def test_write_warnings_are_included_when_present(self) -> None:
        response = {
            "agent_may_continue": True,
            "workroot_view": {"focus": "quick", "confidence": "medium", "task_brief": "Answer"},
            "workroot_contract": {
                "next_exchange": {"action": "none", "reason": "no_exchange_needed", "required": False},
                "commit_contract": {"lease_id": None, "accepted_shapes": [], "required_before_stop": []},
                "state_refs": {},
            },
            "result": {"accepted": False, "status": "rejected", "warnings": ["Needs sync"]},
        }

        packet = build_private_packet(response, adapter="cli", agent="codex")

        self.assertEqual(packet["write"]["warnings"], ["Needs sync"])

    def test_rejected_write_packet_prevents_same_commit_retry_loop(self) -> None:
        response = {
            "agent_may_continue": True,
            "workroot_view": {"focus": "new_work", "confidence": "low", "task_brief": "Call sync before retrying."},
            "workroot_contract": {
                "next_exchange": {"action": "sync", "reason": "resync_required", "required": False},
                "commit_contract": {
                    "lease_id": None,
                    "accepted_shapes": [],
                    "allowed_commit_kinds": [],
                    "required_before_stop": [],
                },
                "state_refs": {},
            },
            "result": {"accepted": False, "status": "rejected", "warnings": ["event_not_allowed"]},
        }

        packet = build_private_packet(response, adapter="cli", agent="codex")
        rendered = render_private_packet_markdown(response, adapter="cli", agent="codex")

        self.assertFalse(packet["write"]["retry_same_commit"])
        self.assertTrue(packet["write"]["retry_only_after_sync_with_matching_shape"])
        self.assertEqual(packet["write"]["max_same_shape_retry"], 0)
        self.assertIn("Do not retry the same rejected commit", rendered)

    def test_call_when_covers_action_and_shape_timing(self) -> None:
        cases = [
            ("none", "no_exchange_needed", [], "if_needed"),
            ("commit", "start_work", ["checkpoint"], "now"),
            ("commit", "checkpoint", ["continuation_checkpoint"], "before_stop_or_switch"),
            ("commit", "asset_ready", ["asset"], "after_user_visible_file_created"),
            ("commit", "decision_ready", ["decision"], "after_stable_decision"),
            ("commit", "state_sync", ["state_update"], "at_checkpoint"),
        ]
        for action, reason, accepted_shapes, expected_when in cases:
            with self.subTest(action=action, reason=reason, accepted_shapes=accepted_shapes):
                response = {
                    "agent_may_continue": True,
                    "workroot_view": {"focus": "continuation", "confidence": "medium", "task_brief": "Work"},
                    "workroot_contract": {
                        "next_exchange": {"action": action, "reason": reason, "required": False},
                        "commit_contract": {
                            "lease_id": "lease-x",
                            "accepted_shapes": accepted_shapes,
                            "required_before_stop": [],
                        },
                        "state_refs": {},
                    },
                    "result": {"accepted": False, "status": "not_recorded", "warnings": []},
                }

                packet = build_private_packet(response, adapter="cli", agent="codex")

                self.assertEqual(packet["call"]["when"], expected_when)


if __name__ == "__main__":
    unittest.main()
