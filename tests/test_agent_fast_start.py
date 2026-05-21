from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SEED = ROOT / "docs/history/public-seed"


class AgentFastStartTest(unittest.TestCase):
    def test_agent_fast_start_exists(self) -> None:
        path = PUBLIC_SEED / ".workroot/kernel/boot/agent-fast-start.md"
        self.assertTrue(path.exists())
        text = path.read_text(encoding="utf-8")
        self.assertIn("pure greeting", text)
        self.assertIn("space/profile/startup.md", text)
        self.assertIn("continue", text)
        self.assertIn("task_registry.csv", text)

    def test_read_order_uses_fast_start_not_long_contract(self) -> None:
        data = json.loads((PUBLIC_SEED / ".workroot/kernel/boot/read-order.json").read_text(encoding="utf-8"))
        default = data["default_read_order"]
        self.assertIn(".workroot/kernel/boot/agent-fast-start.md", default)
        self.assertNotIn("docs/user-interaction-contract.md", default)

    def test_user_startup_guidance_is_conditional(self) -> None:
        data = json.loads((PUBLIC_SEED / ".workroot/kernel/boot/read-order.json").read_text(encoding="utf-8"))
        default = data["default_read_order"]
        conditional = data["conditional_read_order"]
        self.assertNotIn("space/profile/startup.md", default)
        self.assertTrue(
            any(
                item["when"] == "meaningful_work_with_user_startup_guidance"
                and "space/profile/startup.md" in item["paths"]
                for item in conditional
            )
        )


if __name__ == "__main__":
    unittest.main()
