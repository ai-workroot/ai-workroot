from __future__ import annotations

import unittest


class CommandsPackageTest(unittest.TestCase):
    def test_application_command_modules_expose_entrypoints(self) -> None:
        from ai_workroot.commands import bootstrap_dev
        from ai_workroot.commands import build_context
        from ai_workroot.commands import init_workroot
        from ai_workroot.commands import list_workroots
        from ai_workroot.commands import run_doctor
        from ai_workroot.commands import show_status

        self.assertTrue(callable(init_workroot.initialize_workroot))
        self.assertTrue(callable(list_workroots.list_workroots))
        self.assertTrue(callable(show_status.find_workroot_by_cwd))
        self.assertTrue(callable(build_context.build_context))
        self.assertTrue(callable(run_doctor.run_doctor))
        self.assertTrue(callable(run_doctor.run_release_doctor))
        self.assertTrue(callable(bootstrap_dev.bootstrap_dev))


if __name__ == "__main__":
    unittest.main()
