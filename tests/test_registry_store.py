from __future__ import annotations

import csv
import multiprocessing as mp
import tempfile
import unittest
from pathlib import Path

from ai_workroot.runtime.legacy_seed import client as legacy_client
from ai_workroot.runtime.legacy_seed.client import REGISTRY_HEADERS, WorkrootClient, file_lock

from tests.fixtures.public_seed import copy_repo_with_public_seed


ROOT = Path(__file__).resolve().parents[1]


def create_task(root: str, suffix: int) -> None:
    client = WorkrootClient(root)
    client.create_task(
        title=f"Concurrent Task {suffix}",
        task_id=f"concurrent-task-{suffix}",
        process_level="L0",
        next_action="Review result.",
    )


class RegistryStoreTest(unittest.TestCase):
    def copy_workroot(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        tmp = tempfile.TemporaryDirectory()
        work = Path(tmp.name) / "workroot"
        copy_repo_with_public_seed(work)
        return tmp, work

    def test_concurrent_task_creates_do_not_corrupt_registry(self) -> None:
        tmp, work = self.copy_workroot()
        with tmp:
            processes = [mp.Process(target=create_task, args=(str(work), i)) for i in range(8)]
            for process in processes:
                process.start()
            for process in processes:
                process.join()
                self.assertEqual(process.exitcode, 0)

            registry = work / ".workroot/runtime/index/task_registry.csv"
            with registry.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            self.assertEqual(reader.fieldnames, REGISTRY_HEADERS[".workroot/runtime/index/task_registry.csv"])
            created_ids = {row["task_id"] for row in rows if row["task_id"].startswith("concurrent-task-")}
            self.assertEqual(created_ids, {f"concurrent-task-{i}" for i in range(8)})

    def test_file_lock_records_owner_and_releases(self) -> None:
        tmp, work = self.copy_workroot()
        with tmp:
            lock = work / ".workroot/runtime/locks/workroot.lock"
            with file_lock(lock):
                text = lock.read_text(encoding="utf-8")
                self.assertIn("pid=", text)
                self.assertIn("created_at=", text)
            self.assertFalse(lock.exists())

    def test_batch_mode_uses_one_outer_lock(self) -> None:
        tmp, work = self.copy_workroot()
        calls: list[Path] = []
        original = legacy_client.file_lock

        def counting_lock(path: Path, timeout: float = 10.0):
            calls.append(path)
            return original(path, timeout)

        with tmp:
            batch = work / "batch.json"
            batch.write_text(
                '{"operations":[{"op":"task.create","title":"A","task_id":"a"},{"op":"task.create","title":"B","task_id":"b"}]}',
                encoding="utf-8",
            )
            legacy_client.file_lock = counting_lock
            try:
                WorkrootClient(work).apply_batch(str(batch))
            finally:
                legacy_client.file_lock = original

        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
