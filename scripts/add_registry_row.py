#!/usr/bin/env python3
"""Append a row to an AI Workroot CSV registry with uniqueness checks."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


REGISTRY_KEYS = {
    "task": (".workroot/runtime/index/task_registry.csv", ["task_id"]),
    "artifact": (".workroot/runtime/index/artifact_registry.csv", ["artifact_id"]),
    "decision": (".workroot/runtime/index/decision_registry.csv", ["decision_id"]),
    "mind": (".workroot/runtime/index/mind_registry.csv", ["mind_id"]),
    "link": (
        ".workroot/runtime/index/link_registry.csv",
        ["link_id"],
    ),
    "capability": (".workroot/extensions/capability_registry.csv", ["capability_id"]),
}


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registry", choices=sorted(REGISTRY_KEYS))
    parser.add_argument("values", nargs="+", help="key=value fields to append")
    args = parser.parse_args()

    rel_path, key_fields = REGISTRY_KEYS[args.registry]
    path = Path(rel_path)
    if not path.exists():
        raise SystemExit(f"registry not found: {rel_path}")

    fieldnames, rows = read_rows(path)
    row: dict[str, str] = {field: "" for field in fieldnames}
    for item in args.values:
        if "=" not in item:
            raise SystemExit(f"expected key=value, got: {item}")
        key, value = item.split("=", 1)
        if key not in row:
            raise SystemExit(f"unknown field for {rel_path}: {key}")
        row[key] = value

    missing_keys = [field for field in key_fields if not row.get(field)]
    if missing_keys:
        raise SystemExit(f"missing key fields: {', '.join(missing_keys)}")

    new_key = tuple(row[field] for field in key_fields)
    for existing in rows:
        existing_key = tuple(existing.get(field, "") for field in key_fields)
        if existing_key == new_key:
            print(f"registry row already exists: {new_key}")
            return

    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerow(row)

    print(f"added {args.registry}: {new_key}")


if __name__ == "__main__":
    main()
