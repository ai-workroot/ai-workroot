from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def run_workroot_cli(
    env: dict[str, str],
    *args: str,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    process_env = {**os.environ, **env}
    process_env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "ai_workroot", *args],
        cwd=cwd or ROOT,
        env=process_env,
        text=True,
        capture_output=True,
        check=False,
    )
