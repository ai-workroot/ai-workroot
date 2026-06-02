from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from ai_workroot.commands.agent_exchange import (
    build_commit_request_from_shape,
    render_agent_response,
    run_commit_request,
    run_commit_shape,
    run_exchange_request,
    run_sync_request,
)
from ai_workroot.cli.main import _json_object_arg, _sync_work_signal, main


class AgentExchangeCommandTest(unittest.TestCase):
    def test_exchange_delegates_sync_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_path = Path(tmp) / "request.json"
            request = {"protocol_version": "workroot.v1", "request_id": "req-sync"}
            request_path.write_text(json.dumps({"action": "sync", "request": request}), encoding="utf-8")

            with patch("ai_workroot.commands.agent_exchange.controller.sync", return_value={"ok": True}) as sync:
                response = run_exchange_request(request_path)

        self.assertEqual(response, {"ok": True})
        sync.assert_called_once_with(request)

    def test_exchange_delegates_commit_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_path = Path(tmp) / "request.json"
            request = {"protocol_version": "workroot.v1", "request_id": "req-commit"}
            request_path.write_text(json.dumps({"action": "commit", "request": request}), encoding="utf-8")

            with patch("ai_workroot.commands.agent_exchange.controller.commit", return_value={"ok": True}) as commit:
                response = run_exchange_request(request_path)

        self.assertEqual(response, {"ok": True})
        commit.assert_called_once_with(request)

    def test_exchange_rejects_unknown_action_as_protocol_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_path = Path(tmp) / "request.json"
            request_path.write_text(json.dumps({"action": "unknown", "request": {}}), encoding="utf-8")

            response = run_exchange_request(request_path)

        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "invalid_exchange_action")
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "sync")

    def test_sync_helper_builds_protocol_request(self) -> None:
        with patch("ai_workroot.commands.agent_exchange.controller.sync", return_value={"ok": True}) as sync:
            response = run_sync_request(
                request_id="req-sync",
                agent_name="codex",
                cwd=Path("/tmp/workspace"),
                query="Continue task",
                reason="before_work",
                known_state={"task_id": "task-1"},
            )

        self.assertEqual(response, {"ok": True})
        sync.assert_called_once_with(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": "/tmp/workspace",
                "reason": "before_work",
                "query": "Continue task",
                "known_state": {"task_id": "task-1"},
                "work_signal": {},
            }
        )

    def test_sync_helper_passes_work_signal(self) -> None:
        with patch("ai_workroot.commands.agent_exchange.controller.sync", return_value={"ok": True}) as sync:
            response = run_sync_request(
                request_id="req-sync",
                agent_name="codex",
                cwd=Path("/tmp/workspace"),
                query="Continue task",
                reason="before_work",
                work_signal={"phase": "executing", "focus": "Continue task."},
            )

        self.assertEqual(response, {"ok": True})
        self.assertEqual(sync.call_args.args[0]["work_signal"]["phase"], "executing")

    def test_commit_helper_reads_commit_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_path = Path(tmp) / "commit.json"
            request = {"protocol_version": "workroot.v1", "request_id": "req-commit"}
            request_path.write_text(json.dumps(request), encoding="utf-8")

            with patch("ai_workroot.commands.agent_exchange.controller.commit", return_value={"ok": True}) as commit:
                response = run_commit_request(request_path)

        self.assertEqual(response, {"ok": True})
        commit.assert_called_once_with(request)

    def test_commit_helper_returns_protocol_error_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_path = Path(tmp) / "commit.json"
            request_path.write_text(json.dumps({"request_id": "req-bad-commit"}), encoding="utf-8")

            response = run_commit_request(request_path)

        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "missing_protocol_version")
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "sync")

    def test_start_work_shape_builds_deterministic_canonical_intent_request(self) -> None:
        request = build_commit_request_from_shape(
            shape="start_work",
            lease_id="lease-1",
            agent_name="codex",
            title="Release review",
            summary="Review release readiness",
            cwd=Path("/tmp/workspace"),
            persistence="normal",
            occurred_at="2026-05-27T00:00:00Z",
        )
        repeated = build_commit_request_from_shape(
            shape="start-work",
            lease_id="lease-1",
            agent_name="codex",
            title="Release review",
            summary="Review release readiness",
            cwd=Path("/tmp/workspace"),
            persistence="normal",
            occurred_at="2026-05-27T00:00:00Z",
        )

        self.assertEqual(request, repeated)
        self.assertEqual(request["protocol_version"], "workroot.v1")
        self.assertEqual(request["exchange_lease_id"], "lease-1")
        self.assertEqual(request["cwd"], "/tmp/workspace")
        self.assertTrue(request["request_id"].startswith("req-auto-"))
        self.assertTrue(request["idempotency_key"].startswith("idem-auto-"))
        event = request["events"][0]
        self.assertTrue(event["event_id"].startswith("evt-auto-"))
        self.assertEqual(event["kind"], "intent")
        self.assertEqual(event["schema_version"], "intent.v1")
        self.assertEqual(event["source"]["actor_name"], "codex")
        self.assertEqual(event["payload"]["intent_text"], "Review release readiness")
        self.assertEqual(event["payload"]["classification"]["persistence"], "normal")
        self.assertEqual(event["payload"]["task_hint"]["title"], "Release review")

    def test_commit_cli_accepts_protocol_shape_names_with_underscores(self) -> None:
        with patch("ai_workroot.commands.agent_exchange.controller.commit", return_value={"ok": True}) as commit:
            output = StringIO()
            with redirect_stdout(output):
                rc = main(
                    [
                        "agent",
                        "commit",
                        "--format",
                        "json",
                        "--shape",
                        "start_work",
                        "--lease",
                        "lease-1",
                        "--title",
                        "Release review",
                        "--summary",
                        "Review release readiness",
                    ]
                )

        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(output.getvalue()), {"ok": True})
        self.assertEqual(commit.call_args.args[0]["events"][0]["kind"], "intent")

    def test_checkpoint_shape_maps_done_items_without_task_refs(self) -> None:
        request = build_commit_request_from_shape(
            shape="checkpoint",
            lease_id="lease-progress",
            agent_name="codex",
            summary="Tests pass",
            done=("Run unit tests", "Run release validation"),
            occurred_at="2026-05-27T00:00:00Z",
        )

        event = request["events"][0]
        self.assertEqual(event["kind"], "progress")
        self.assertEqual(event["payload"]["summary"], "Tests pass")
        self.assertNotIn("task_id", event["payload"])
        self.assertNotIn("run_id", event["payload"])
        self.assertEqual(
            event["payload"]["items_created"],
            [
                {"title": "Run unit tests", "status": "done", "result_summary": "Run unit tests"},
                {
                    "title": "Run release validation",
                    "status": "done",
                    "result_summary": "Run release validation",
                },
            ],
        )

    def test_checkpoint_shape_filters_empty_item_placeholders(self) -> None:
        request = build_commit_request_from_shape(
            shape="checkpoint",
            lease_id="lease-progress",
            agent_name="codex",
            summary="Checkpoint summary.",
            done=("None.", "Completed real work"),
            open=("N/A", "Follow up with a real next step"),
            blocked=("none",),
            occurred_at="2026-05-27T00:00:00Z",
        )

        event = request["events"][0]
        self.assertEqual(
            event["payload"]["items_created"],
            [
                {
                    "title": "Completed real work",
                    "status": "done",
                    "result_summary": "Completed real work",
                },
                {
                    "title": "Follow up with a real next step",
                    "status": "todo",
                    "result_summary": None,
                },
            ],
        )

    def test_commit_cli_accepts_contract_field_aliases_for_checkpoint(self) -> None:
        with patch("ai_workroot.commands.agent_exchange.controller.commit", return_value={"ok": True}) as commit:
            output = StringIO()
            with redirect_stdout(output):
                rc = main(
                    [
                        "agent",
                        "commit",
                        "--format",
                        "json",
                        "--shape",
                        "checkpoint",
                        "--lease",
                        "lease-progress",
                        "--summary",
                        "Checkpoint summary.",
                        "--target-ref",
                        "task-1",
                        "--changed-steps-or-results",
                        "Captured the important checkpoint result.",
                    ]
                )

        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(output.getvalue()), {"ok": True})
        event = commit.call_args.args[0]["events"][0]
        self.assertEqual(event["payload"]["task_id"], "task-1")
        self.assertEqual(
            event["payload"]["items_created"],
            [
                {
                    "title": "Captured the important checkpoint result.",
                    "status": "done",
                    "result_summary": "Captured the important checkpoint result.",
                }
            ],
        )

    def test_continuation_shape_maps_state_and_next_aliases_to_internal_handoff_event(self) -> None:
        request = build_commit_request_from_shape(
            shape="continuation",
            lease_id="lease-handoff",
            agent_name="codex",
            state="Tests pass",
            next="Review diff",
            task_id="task-1",
            run_id="run-1",
            occurred_at="2026-05-27T00:00:00Z",
        )

        event = request["events"][0]
        self.assertEqual(event["kind"], "handoff")
        self.assertEqual(event["payload"]["task_id"], "task-1")
        self.assertEqual(event["payload"]["run_id"], "run-1")
        self.assertEqual(event["payload"]["current_state"], "Tests pass")
        self.assertEqual(event["payload"]["next_action"], "Review diff")

    def test_continuation_shape_uses_summary_as_state_when_state_and_next_are_missing(self) -> None:
        request = build_commit_request_from_shape(
            shape="continuation",
            lease_id="lease-handoff",
            agent_name="codex",
            summary="Ready to continue from the latest checkpoint.",
            occurred_at="2026-05-27T00:00:00Z",
        )

        event = request["events"][0]
        self.assertEqual(event["kind"], "handoff")
        self.assertEqual(event["payload"]["current_state"], "Ready to continue from the latest checkpoint.")
        self.assertEqual(event["payload"]["next_action"], "")

    def test_state_update_shape_maps_to_internal_state_event(self) -> None:
        request = build_commit_request_from_shape(
            shape="state-update",
            lease_id="lease-state",
            agent_name="codex",
            target="task:task-1",
            change="status active -> paused",
            occurred_at="2026-05-27T00:00:00Z",
        )

        event = request["events"][0]
        self.assertEqual(event["kind"], "state")
        self.assertEqual(event["schema_version"], "state.v1")
        self.assertEqual(event["payload"]["target_type"], "task")
        self.assertEqual(event["payload"]["target_id"], "task-1")
        self.assertEqual(event["payload"]["from_status"], "active")
        self.assertEqual(event["payload"]["to_status"], "paused")

    def test_asset_shape_maps_to_internal_asset_event_payload(self) -> None:
        request = build_commit_request_from_shape(
            shape="asset",
            lease_id="lease-asset",
            agent_name="codex",
            title="Protocol design",
            path="docs/protocol.md",
            asset_kind="design_doc",
            summary="Final protocol design.",
            status="current",
            task_id="task-1",
            run_id="run-1",
            occurred_at="2026-05-27T00:00:00Z",
        )

        event = request["events"][0]
        self.assertEqual(event["kind"], "asset")
        self.assertEqual(event["schema_version"], "asset.v1")
        self.assertEqual(event["payload"]["title"], "Protocol design")
        self.assertEqual(event["payload"]["path"], "docs/protocol.md")
        self.assertEqual(event["payload"]["asset_kind"], "design_doc")
        self.assertEqual(event["payload"]["status"], "current")
        self.assertEqual(event["payload"]["task_id"], "task-1")
        self.assertEqual(event["payload"]["run_id"], "run-1")

    def test_asset_shape_derives_title_from_path_when_missing(self) -> None:
        request = build_commit_request_from_shape(
            shape="asset",
            lease_id="lease-asset",
            agent_name="codex",
            path="results/operating-brief.md",
            summary="Operating brief.",
            occurred_at="2026-05-27T00:00:00Z",
        )

        event = request["events"][0]
        self.assertEqual(event["payload"]["title"], "Operating Brief")
        self.assertEqual(event["payload"]["path"], "results/operating-brief.md")

    def test_decision_shape_maps_to_internal_decision_event_payload(self) -> None:
        request = build_commit_request_from_shape(
            shape="decision",
            lease_id="lease-decision",
            agent_name="codex",
            title="Protocol entry",
            decision="Expose shape-native commit.",
            reason_text="LLM should not see internal event kinds.",
            scope="agent-protocol",
            task_id="task-1",
            run_id="run-1",
            occurred_at="2026-05-27T00:00:00Z",
        )

        event = request["events"][0]
        self.assertEqual(event["kind"], "decision")
        self.assertEqual(event["schema_version"], "decision.v1")
        self.assertEqual(event["payload"]["title"], "Protocol entry")
        self.assertEqual(event["payload"]["decision"], "Expose shape-native commit.")
        self.assertEqual(event["payload"]["reason"], "LLM should not see internal event kinds.")
        self.assertEqual(event["payload"]["scope"], "agent-protocol")
        self.assertEqual(event["payload"]["task_id"], "task-1")
        self.assertEqual(event["payload"]["run_id"], "run-1")

    def test_guidance_format_renders_only_model_guidance(self) -> None:
        rendered = render_agent_response(
            {
                "workroot_guidance": "## Workroot Guidance\nUse privately.\n",
                "workroot_contract": {"commit_contract": {"lease_id": "lease-secret"}},
                "result": {"status": "applied"},
            },
            output_format="guidance",
        )

        self.assertEqual(rendered, "## Workroot Guidance\nUse privately.\n")
        self.assertNotIn("lease-secret", rendered)
        self.assertNotIn("workroot_contract", rendered)

    def test_packet_format_renders_private_packet_without_internal_contract(self) -> None:
        rendered = render_agent_response(
            {
                "agent_may_continue": True,
                "workroot_view": {"focus": "new_work", "confidence": "high", "task_brief": "Plan protocol"},
                "workroot_contract": {
                    "next_exchange": {"action": "commit", "reason": "start_work", "required": False},
                    "commit_contract": {"lease_id": "lease-1", "accepted_shapes": ["start_work"]},
                    "state_refs": {},
                    "debug": {"lease_secret": "do-not-render"},
                },
                "result": {"accepted": False, "status": "not_recorded", "warnings": []},
            },
            output_format="packet",
            agent="codex",
        )

        self.assertIn("## Workroot Private Packet", rendered)
        self.assertIn('"v": "workroot.packet.v1"', rendered)
        self.assertIn("--shape start-work --lease lease-1", rendered)
        self.assertNotIn("workroot_contract", rendered)
        self.assertNotIn("do-not-render", rendered)

    def test_run_commit_shape_delegates_canonical_request_to_controller(self) -> None:
        with patch("ai_workroot.commands.agent_exchange.controller.commit", return_value={"ok": True}) as commit:
            response = run_commit_shape(
                shape="start_work",
                lease_id="lease-1",
                agent_name="codex",
                title="Release review",
                summary="Review release readiness",
                occurred_at="2026-05-27T00:00:00Z",
            )

        self.assertEqual(response, {"ok": True})
        request = commit.call_args.args[0]
        self.assertEqual(request["events"][0]["kind"], "intent")
        self.assertEqual(request["events"][0]["payload"]["task_hint"]["title"], "Release review")

    def test_plain_text_known_state_and_work_signal_are_tolerated(self) -> None:
        self.assertEqual(
            _json_object_arg("recovering from previous task", "--known-state"),
            {"note": "recovering from previous task"},
        )
        self.assertEqual(
            _json_object_arg("review founder operating plan", "--work-signal"),
            {"focus": "review founder operating plan"},
        )
        self.assertEqual(
            _json_object_arg("new_work", "--work-signal"),
            {"focus": "new_work", "intended_action": "plan", "phase": "switching", "work_kind": "task"},
        )
        self.assertEqual(
            _json_object_arg("phase=switching, work_kind=task, intended_action=plan", "--work-signal"),
            {"phase": "switching", "work_kind": "task", "intended_action": "plan"},
        )

    def test_sync_persistence_hint_maps_to_work_signal_without_overriding_explicit_kind(self) -> None:
        self.assertEqual(
            _sync_work_signal({"focus": "loose questions"}, persistence="temporary"),
            {
                "focus": "loose questions",
                "intended_action": "preserve",
                "phase": "switching",
                "work_kind": "inbox",
            },
        )
        self.assertEqual(
            _sync_work_signal({"work_kind": "task", "focus": "normal work"}, persistence="temporary"),
            {"work_kind": "task", "focus": "normal work"},
        )

    def test_sync_cli_accepts_persistence_hint_for_agent_tolerance(self) -> None:
        with patch("ai_workroot.cli.main.run_sync_request", return_value={"ok": True}) as sync:
            output = StringIO()
            with redirect_stdout(output):
                rc = main(
                    [
                        "agent",
                        "sync",
                        "--agent",
                        "codex",
                        "--cwd",
                        ".",
                        "--query",
                        "Temporary inbox",
                        "--persistence",
                        "temporary",
                    ]
                )

        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(output.getvalue()), {"ok": True})
        self.assertEqual(sync.call_args.kwargs["work_signal"]["work_kind"], "inbox")
        self.assertEqual(sync.call_args.kwargs["work_signal"]["phase"], "switching")

    def test_sync_cli_accepts_split_work_signal_flags_for_agent_tolerance(self) -> None:
        with patch("ai_workroot.cli.main.run_sync_request", return_value={"ok": True}) as sync:
            output = StringIO()
            with redirect_stdout(output):
                rc = main(
                    [
                        "agent",
                        "sync",
                        "--agent",
                        "codex",
                        "--cwd",
                        ".",
                        "--query",
                        "Create results/plan.md and preserve it as an asset",
                        "--reason",
                        "before_task_switch",
                        "--phase",
                        "switching",
                        "--work-kind",
                        "task",
                        "--intended-action",
                        "plan",
                        "--focus",
                        "plan asset",
                    ]
                )

        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(output.getvalue()), {"ok": True})
        self.assertEqual(
            sync.call_args.kwargs["work_signal"],
            {
                "phase": "switching",
                "work_kind": "task",
                "intended_action": "plan",
                "focus": "plan asset",
            },
        )

    def test_sync_cli_accepts_signal_alias_for_work_signal(self) -> None:
        with patch("ai_workroot.cli.main.run_sync_request", return_value={"ok": True}) as sync:
            output = StringIO()
            with redirect_stdout(output):
                rc = main(
                    [
                        "agent",
                        "sync",
                        "--query",
                        "Continue current work.",
                        "--reason",
                        "before_task_switch",
                        "--signal",
                        "phase=switching,work_kind=task,intended_action=plan",
                    ]
                )

        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(output.getvalue()), {"ok": True})
        self.assertEqual(
            sync.call_args.kwargs["work_signal"],
            {"phase": "switching", "work_kind": "task", "intended_action": "plan"},
        )

    def test_sync_cli_accepts_trailing_key_value_work_signal_parts_for_agent_tolerance(self) -> None:
        with patch("ai_workroot.cli.main.run_sync_request", return_value={"ok": True}) as sync:
            output = StringIO()
            with redirect_stdout(output):
                rc = main(
                    [
                        "agent",
                        "sync",
                        "--reason",
                        "before_task_switch",
                        "--query",
                        "Quick answer only.",
                        "phase=switching",
                        "work_kind=task",
                        "intended_action=plan",
                    ]
                )

        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(output.getvalue()), {"ok": True})
        self.assertEqual(
            sync.call_args.kwargs["work_signal"],
            {"phase": "switching", "work_kind": "task", "intended_action": "plan"},
        )

    def test_run_commit_shape_missing_lease_reaches_controller_as_resyncable_protocol_request(self) -> None:
        with patch(
            "ai_workroot.commands.agent_exchange.controller.commit",
            return_value={"result": {"status": "rejected"}, "workroot_contract": {"next_exchange": {"action": "sync"}}},
        ) as commit:
            response = run_commit_shape(
                shape="checkpoint",
                lease_id="",
                agent_name="codex",
                cwd=Path("/tmp/workspace"),
                summary="Progress summary.",
            )

        self.assertEqual(response["result"]["status"], "rejected")
        request = commit.call_args.args[0]
        self.assertEqual(request["exchange_lease_id"], "")
        self.assertEqual(request["cwd"], "/tmp/workspace")

    def test_run_commit_shape_missing_continuation_fields_returns_protocol_response(self) -> None:
        response = run_commit_shape(
            shape="continuation",
            lease_id="lease-1",
            agent_name="codex",
            cwd=Path("/tmp/workspace"),
        )

        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "missing_shape_fields")
        self.assertTrue(response["agent_may_continue"])
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "sync")


if __name__ == "__main__":
    unittest.main()
