from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ai_workroot.state.layout import (
    CleanModeBoundaryError,
    assert_clean_mode_boundary,
    resolve_ai_workroot_home,
    workroot_state_dir,
)


class WorkrootPathsTest(unittest.TestCase):
    def test_env_override_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"AI_WORKROOT_HOME": tmp}):
                self.assertEqual(resolve_ai_workroot_home(), Path(tmp).resolve())

    def test_macos_linux_default(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("platform.system", return_value="Darwin"):
                with mock.patch("pathlib.Path.home", return_value=Path("/Users/example")):
                    home = resolve_ai_workroot_home()
        self.assertEqual(home, Path("/Users/example/.ai-workroot"))

    def test_explicit_home_argument_wins_when_env_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {}, clear=True):
                self.assertEqual(resolve_ai_workroot_home(Path(tmp)), Path(tmp).resolve())

    def test_explicit_home_argument_wins_over_env(self) -> None:
        with tempfile.TemporaryDirectory() as explicit:
            with tempfile.TemporaryDirectory() as env_home:
                with mock.patch.dict(os.environ, {"AI_WORKROOT_HOME": env_home}):
                    self.assertEqual(resolve_ai_workroot_home(Path(explicit)), Path(explicit).resolve())

    def test_windows_default(self) -> None:
        with mock.patch.dict(os.environ, {"LOCALAPPDATA": r"C:\Users\Example\AppData\Local"}, clear=True):
            with mock.patch("platform.system", return_value="Windows"):
                home = resolve_ai_workroot_home()
        self.assertEqual(home, Path(r"C:\Users\Example\AppData\Local\AIWorkroot"))

    def test_state_dir_uses_workroots_namespace(self) -> None:
        base = Path("/tmp/ai-workroot-home")
        self.assertEqual(workroot_state_dir(base, "wr_demo"), base / "workroots" / "wr_demo")

    def test_clean_mode_rejects_state_inside_user_directory(self) -> None:
        with self.assertRaises(CleanModeBoundaryError):
            assert_clean_mode_boundary(Path("/tmp/project"), Path("/tmp/project/.ai-workroot/workroots/wr_demo"))

    def test_clean_mode_allows_state_outside_user_directory(self) -> None:
        assert_clean_mode_boundary(Path("/tmp/project"), Path("/tmp/.ai-workroot/workroots/wr_demo"))


if __name__ == "__main__":
    unittest.main()
