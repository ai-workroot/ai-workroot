from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_workroot.indexing.legacy_fts import (
    chunk_markdown,
    chunk_plain_text,
    index_text_file,
    is_binary_file,
    search_fts,
)
from ai_workroot.storage.legacy_sqlite import initialize_workroot_sqlite, open_sqlite


class WorkrootIndexingTest(unittest.TestCase):
    def open_db(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db_path = Path(tmp.name) / "workroot.sqlite"
        initialize_workroot_sqlite(db_path)
        return tmp, open_sqlite(db_path)

    def test_markdown_heading_chunking_uses_latest_heading(self) -> None:
        text = "# Project\nIntro\n\n## Clean Mode\nState stays outside user folders.\n\n## Doctor\nReports problems.\n"

        chunks = chunk_markdown(text, max_chars=500)

        self.assertEqual([chunk.heading for chunk in chunks], ["Project", "Clean Mode", "Doctor"])
        self.assertIn("State stays outside", chunks[1].body)

    def test_plain_text_chunking_splits_bounded_chunks(self) -> None:
        text = "alpha beta gamma delta epsilon"

        chunks = chunk_plain_text(text, max_chars=12)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk.body) <= 12 for chunk in chunks))

    def test_binary_files_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "image.bin"
            binary.write_bytes(b"\x00\x01\x02\x03")

            self.assertTrue(is_binary_file(binary))

    def test_index_and_search_fts_returns_explainable_metadata(self) -> None:
        tmp, conn = self.open_db()
        with tmp, conn:
            root = Path(tmp.name) / "project"
            root.mkdir()
            doc = root / "notes.md"
            doc.write_text("# Decisions\nClean Mode keeps managed state outside user folders.\n", encoding="utf-8")

            result = index_text_file(
                conn,
                workroot_id="wr_demo",
                root_directory=root,
                path=doc,
                indexed_at="2026-05-19T00:00:00Z",
            )
            matches = search_fts(conn, "wr_demo", "managed state", limit=5)

            self.assertEqual(result.status, "indexed")
            self.assertEqual(matches[0]["relativePath"], "notes.md")
            self.assertEqual(matches[0]["heading"], "Decisions")
            self.assertIn("managed", matches[0]["snippet"].lower())
            self.assertIn("score", matches[0])
            self.assertEqual(matches[0]["reason"], "fts-match")

    def test_malformed_fts_query_returns_no_matches(self) -> None:
        tmp, conn = self.open_db()
        with tmp, conn:
            root = Path(tmp.name) / "project"
            root.mkdir()
            doc = root / "notes.md"
            doc.write_text("# Notes\nClean Mode context is searchable.\n", encoding="utf-8")
            index_text_file(conn, "wr_demo", root, doc, indexed_at="2026-05-19T00:00:00Z")

            matches = search_fts(conn, "wr_demo", "clean OR", limit=5)

            self.assertEqual(matches, [])


if __name__ == "__main__":
    unittest.main()
