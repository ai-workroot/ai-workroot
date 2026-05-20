from __future__ import annotations

import unittest

from ai_workroot.contracts.clock import Clock
from ai_workroot.contracts.events import EventPublisher, EventRecord
from ai_workroot.contracts.filesystem import FileInfo, FileSystem
from ai_workroot.contracts.git import GitStatus, GitStatusProvider
from ai_workroot.contracts.retrieval import RetrievalProvider, RetrievalQuery, RetrievalResult
from ai_workroot.contracts.storage import KeyValueStore, StoredRecord
from ai_workroot.contracts.templates import TemplateRenderer


class ContractsTest(unittest.TestCase):
    def test_storage_record_is_independent_dto(self) -> None:
        record = StoredRecord(key="workroot", value={"id": "wr_demo"}, version="1")

        self.assertEqual(record.key, "workroot")
        self.assertEqual(record.value["id"], "wr_demo")

    def test_retrieval_query_and_result_dtos(self) -> None:
        query = RetrievalQuery(query="Clean Workroot", workroot_id="wr_demo", limit=5)
        result = RetrievalResult(source_id="asset_1", title="Spec", score=0.8, metadata={"provider": "fts"})

        self.assertEqual(query.limit, 5)
        self.assertEqual(result.metadata["provider"], "fts")

    def test_protocols_are_runtime_checkable(self) -> None:
        for protocol in (
            Clock,
            EventPublisher,
            FileSystem,
            GitStatusProvider,
            RetrievalProvider,
            KeyValueStore,
            TemplateRenderer,
        ):
            self.assertTrue(hasattr(protocol, "_is_runtime_protocol"))

    def test_filesystem_and_git_dtos(self) -> None:
        file_info = FileInfo(path="README.md", size_bytes=10, modified_at="2026-05-20T00:00:00Z")
        git_status = GitStatus(branch="main", is_dirty=False, head="abc123")
        event = EventRecord(event_type="created", payload={"id": "wr_demo"})

        self.assertEqual(file_info.path, "README.md")
        self.assertFalse(git_status.is_dirty)
        self.assertEqual(event.payload["id"], "wr_demo")


if __name__ == "__main__":
    unittest.main()
