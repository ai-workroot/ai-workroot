from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_workroot.commands.agent_exchange import run_commit_request, run_exchange_request, run_sync_request


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
        self.assertEqual(response["directive"]["type"], "resync_required")

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
            }
        )

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
        self.assertEqual(response["directive"]["type"], "resync_required")


if __name__ == "__main__":
    unittest.main()
