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
        self.assertEqual(packet["refs"], {"exchange": "lease-1"})
        self.assertEqual(packet["write"]["status"], "not_recorded")
        self.assertEqual(packet["write"]["meaning"], "No durable fact was written.")
        self.assertNotIn("warnings", packet["write"])
        self.assertIn("--lease lease-1", packet["adapter_hint"]["cli"])
        self.assertIn("--shape start-work", packet["adapter_hint"]["cli"])
        self.assertNotIn("quick", packet["adapter_hint"]["cli"])
        serialized = json.dumps(packet, ensure_ascii=False)
        self.assertNotIn("debug", serialized)
        self.assertNotIn("effects", serialized)

    def test_continuation_packet_limits_open_and_done_items(self) -> None:
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
                    "required_before_stop": ["continuation_checkpoint"],
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
        self.assertEqual(packet["call"]["also"], ["asset_if_created", "decision_if_made", "continuation_before_stop"])
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
                    "required_before_stop": ["continuation"],
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
            'workroot agent sync --agent codex --cwd . --reason before_work --query "<short intent>"',
            packet["adapter_hint"]["cli"],
        )
        self.assertIn("--work-signal", packet["adapter_hint"]["cli"])
        self.assertEqual(
            packet["call"]["work_signal"],
            {
                "phase": "planning",
                "work_kind": "task",
                "intended_action": "plan",
                "focus": "<short intent>",
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
            'workroot agent sync --agent codex --cwd . --reason before_work --query "<short intent>"',
            packet["adapter_hint"]["cli"],
        )
        self.assertIn("--work-signal", packet["adapter_hint"]["cli"])
        self.assertNotIn("alignment_required", packet["adapter_hint"]["cli"])

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
