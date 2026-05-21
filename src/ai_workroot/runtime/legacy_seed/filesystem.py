"""Filesystem helpers for legacy Public Seed compatibility."""

from __future__ import annotations

from ai_workroot.runtime.legacy_seed.client import (
    append_unique_lines,
    copy_tree_or_file,
    markdown_sections,
    remove_tree_or_file,
    replace_in_file,
    restore_tree_or_file,
)

__all__ = [
    "append_unique_lines",
    "copy_tree_or_file",
    "markdown_sections",
    "remove_tree_or_file",
    "replace_in_file",
    "restore_tree_or_file",
]

