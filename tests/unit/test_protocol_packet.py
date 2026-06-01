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
        self.assertEqual(packet["call"]["fields"], ["title", "summary", "persistence"])
        self.assertEqual(packet["refs"], {"exchange": "lease-1"})
        self.assertEqual(packet["write"]["status"], "not_recorded")
        self.assertIn("--shape start-work", packet["adapter_hint"]["cli"])
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
        self.assertEqual(packet["call"]["also"], ["asset_if_created", "decision_if_made", "continuation_before_stop"])
        self.assertEqual(packet["refs"], {"exchange": "lease-2", "task": "task-1", "run": "run-1"})

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
        self.assertNotIn("shape", packet["call"])
        self.assertIn("adapter_hint", packet)
        self.assertEqual(
            packet["adapter_hint"]["cli"],
            "workroot agent sync --agent codex --cwd . --reason before_work --query <short intent>",
        )


if __name__ == "__main__":
    unittest.main()
