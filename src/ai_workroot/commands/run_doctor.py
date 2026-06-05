"""Doctor application command."""

from __future__ import annotations

from ai_workroot.capabilities.system_health.doctor import run_doctor, run_release_doctor


__all__ = ["run_doctor", "run_release_doctor"]
