from __future__ import annotations


def parse_token_usage(output: str) -> int:
    for line in output.splitlines():
        if line.startswith("TokenUsage:"):
            usage = line.split(":", 1)[1].strip().split("/", 1)[0]
            return int(usage)
    raise AssertionError("missing TokenUsage line")
