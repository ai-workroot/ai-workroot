from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.commands.agent_exchange import build_commit_request_from_shape
from ai_workroot.protocol.controller import commit, sync
from ai_workroot.protocol.response import workroot_contract_from_lease
from ai_workroot.state.environment import initialize_environment, register_workroot
from ai_workroot.state.layout import workroot_sqlite_path
from ai_workroot.state.sqlite import initialize_workroot_sqlite


class ProtocolResponseV2Test(unittest.TestCase):
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
        initialize_workroot_sqlite(workroot_sqlite_path(Path(self.registration.state_directory)))
        self.previous_home = os.environ.get("AI_WORKROOT_HOME")
        os.environ["AI_WORKROOT_HOME"] = str(self.home)
        self.addCleanup(self.restore_home)

    def restore_home(self) -> None:
        if self.previous_home is None:
            os.environ.pop("AI_WORKROOT_HOME", None)
        else:
            os.environ["AI_WORKROOT_HOME"] = self.previous_home

    def test_sync_response_uses_workroot_protocol_bridge_envelope(self) -> None:
        response = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-v2-envelope",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": "Implement the Workroot Agent Protocol v2.",
                "work_signal": {
                    "phase": "planning",
                    "work_kind": "implementation",
                    "intended_action": "plan",
                    "focus": "Workroot Agent Protocol v2",
                },
            }
        )

        for key in (
            "schema_version",
            "protocol_version",
            "server_version",
            "ok",
            "agent_may_continue",
            "workroot_guidance",
            "workroot_contract",
            "workroot_view",
            "result",
            "recovery",
            "error",
        ):
            self.assertIn(key, response)
        for removed in (
            "control_context",
            "work_focus",
            "task_context",
            "directive",
            "continuation_contract",
            "next_call",
            "machine_contract",
            "lease",
            "state_vector",
            "contract",
            "observed_versions",
            "context",
            "state",
        ):
            self.assertNotIn(removed, response)
        self.assertEqual(response["schema_version"], "workroot.agent_response.v1")
        self.assertEqual(response["protocol_version"], "workroot.v1")
        self.assertEqual(response["server_version"], "0.9.531")
        self.assertIn("## Workroot Guidance", response["workroot_guidance"])
        self.assertIn("Use this privately", response["workroot_guidance"])
        self.assertEqual(response["workroot_view"]["focus"], "new_work")
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "commit")
        self.assertEqual(response["workroot_contract"]["commit_contract"]["accepted_shapes"], ["start_work"])
        self.assertIsNotNone(response["workroot_contract"]["commit_contract"]["lease_id"])
        self.assertEqual(response["workroot_contract"]["state_refs"]["work_ref"], "wr_demo")
        self.assertNotIn("debug", response["workroot_contract"])

    def test_commit_response_keeps_effects_in_sqlite_not_protocol_contract_debug(self) -> None:
        sync_response = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-v2-clean-commit",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": "Create clean response task.",
                "work_signal": {"phase": "planning", "work_kind": "task", "intended_action": "plan"},
            }
        )
        response = commit(
            build_commit_request_from_shape(
                shape="start_work",
                lease_id=str(sync_response["workroot_contract"]["commit_contract"]["lease_id"]),
                agent_name="codex",
                title="Clean response task",
                summary="Clean response task.",
                event_id="event-clean-response-task",
            )
        )

        self.assertEqual(response["result"]["status"], "applied")
        self.assertIn("state_refs", response["workroot_contract"])
        self.assertIn("commit_contract", response["workroot_contract"])
        self.assertNotIn("debug", response["workroot_contract"])
        rendered_contract = str(response["workroot_contract"])
        self.assertNotIn("effects", rendered_contract)
        self.assertNotIn("event_results", rendered_contract)
        sqlite_path = workroot_sqlite_path(Path(self.registration.state_directory))
        with sqlite3.connect(sqlite_path) as conn:
            effects_count = conn.execute(
                "SELECT COUNT(*) FROM protocol_event_effects WHERE event_id = 'event-clean-response-task'"
            ).fetchone()[0]
        self.assertGreater(effects_count, 0)

    def test_protocol_error_response_uses_workroot_protocol_bridge_envelope(self) -> None:
        response = sync({"request_id": "req-bad-sync"})

        self.assertFalse(response["ok"])
        self.assertTrue(response["agent_may_continue"])
        self.assertEqual(response["schema_version"], "workroot.agent_response.v1")
        self.assertEqual(response["error"]["code"], "missing_protocol_version")
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "sync")
        self.assertEqual(response["result"]["status"], "resync_required")
        self.assertIn("sync", response["workroot_guidance"])
        for removed in (
            "control_context",
            "directive",
            "continuation_contract",
            "next_call",
            "machine_contract",
            "lease",
            "state_vector",
            "contract",
            "observed_versions",
        ):
            self.assertNotIn(removed, response)

    def test_contract_input_requirements_use_cli_field_names(self) -> None:
        contract = workroot_contract_from_lease(
            {
                "lease_id": "lease-1",
                "allowed_events": ["progress", "state", "decision"],
            },
            next_action="commit",
            reason="continue",
        )

        requirements = contract["commit_contract"]["input_requirements"]

        self.assertIn("summary", requirements)
        self.assertIn("done", requirements)
        self.assertIn("target", requirements)
        self.assertIn("change", requirements)
        self.assertIn("reason_text", requirements)
        self.assertNotIn("changed_steps_or_results", requirements)
        self.assertNotIn("target_ref", requirements)
        self.assertNotIn("state_change", requirements)
        self.assertNotIn("reason", requirements)


if __name__ == "__main__":
    unittest.main()
