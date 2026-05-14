#!/usr/bin/env python3
"""Validate multilingual task naming behavior for AI Workroot."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("new_task.py")
spec = importlib.util.spec_from_file_location("new_task", SCRIPT_PATH)
if spec is None or spec.loader is None:
    raise SystemExit("cannot load new_task.py")

new_task = importlib.util.module_from_spec(spec)
spec.loader.exec_module(new_task)


def check_slug(title: str, expected: str) -> None:
    actual = new_task.slugify(title)
    if actual != expected:
        raise AssertionError(f"slugify({title!r}) = {actual!r}, expected {expected!r}")


def check_unique_identity() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        zh_task = "\u6d4b\u8bd5\u4efb\u52a1"
        instant = "2026-05-15T01:02:03Z"
        existing_id = f"task-20260515-010203-{zh_task}"
        task_dir = root / ".workroot" / "runtime" / "work" / "active" / existing_id
        task_dir.mkdir(parents=True)
        registry = root / ".workroot" / "runtime" / "index" / "task_registry.csv"
        registry.parent.mkdir(parents=True)
        registry.write_text(
            "task_id,title,status,owner_scope,visibility,created_at,updated_at,user_visible_output_path,source_path,handoff_path\n"
            f"{existing_id},{zh_task},active,personal,internal,{instant},{instant},,.workroot/runtime/work/active/{existing_id},.workroot/runtime/work/active/{existing_id}/handoff.md\n",
            encoding="utf-8",
        )
        task_id, path = new_task.unique_task_identity(
            root=root,
            title=zh_task,
            instant=instant,
            requested_id=None,
        )
        if task_id != f"{existing_id}-2":
            raise AssertionError(task_id)
        if path.as_posix() != f"{tmp}/.workroot/runtime/work/active/{existing_id}-2":
            raise AssertionError(path)

        try:
            new_task.unique_task_identity(
                root=root,
                title=zh_task,
                instant=instant,
                requested_id=existing_id,
            )
        except SystemExit as exc:
            if "task_id already exists" not in str(exc):
                raise
        else:
            raise AssertionError("duplicate requested task id should fail")


def main() -> None:
    check_slug("\u6d4b\u8bd5\u4efb\u52a1", "\u6d4b\u8bd5\u4efb\u52a1")
    check_slug("\u4ea7\u54c1\u9700\u6c42\u8bc4\u5ba1", "\u4ea7\u54c1\u9700\u6c42\u8bc4\u5ba1")
    check_slug("\u30c6\u30b9\u30c8\u8a08\u753b", "\u30c6\u30b9\u30c8\u8a08\u753b")
    check_slug("\u0627\u062e\u062a\u0628\u0627\u0631 \u0627\u0644\u0645\u0646\u062a\u062c", "\u0627\u062e\u062a\u0628\u0627\u0631-\u0627\u0644\u0645\u0646\u062a\u062c")
    check_slug("\u0928\u092f\u093e \u0915\u093e\u0930\u094d\u092f", "\u0928\u092f\u093e-\u0915\u093e\u0930\u094d\u092f")
    check_slug("\u0e07\u0e32\u0e19\u0e17\u0e14\u0e2a\u0e2d\u0e1a", "\u0e07\u0e32\u0e19\u0e17\u0e14\u0e2a\u0e2d\u0e1a")
    check_slug("Plan Q2 / Launch 🚀", "plan-q2-launch")
    check_slug("  Multiple   Spaces  ", "multiple-spaces")
    check_slug("!!!", "task")
    check_slug("ＡＩ Workroot", "ai-workroot")
    check_unique_identity()
    print("new_task multilingual tests passed.")


if __name__ == "__main__":
    main()
