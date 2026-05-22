from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLIC_SEED = ROOT / "docs/history/public-seed"
TEXT_SUFFIXES = {".md", ".json", ".csv", ".py", ".yml", ".yaml", ".txt", ".sql"}
CURRENT_DOC_ROOTS = (
    ROOT / "README.md",
    ROOT / "ROADMAP.md",
    ROOT / "START_HERE_FOR_HUMANS.md",
    ROOT / "docs",
)
HISTORICAL_DOC_PREFIXES = (
    ROOT / "docs/history",
    ROOT / "docs/releases",
    ROOT / "docs/incidents",
)
NOVICE_INTERNAL_TERMS = [
    ".workroot",
    "kernel",
    "registry",
    "schema",
    "runtime",
]
FORBIDDEN_TEXT_PATTERNS = [
    ".".join(["0", "9", "0"]),
    "v" + ".".join(["0", "9", "0"]),
    "Un" + "released",
    "actor" + "_" + "registry",
    "owner" + "_" + "id",
    "parent" + "_" + "task" + "_" + "id",
    "migrate" + "_" + "workroot",
    "validate" + "_" + "workroot",
    "migration" + "_" + "registry",
    "migration" + "-" + "policy",
]


def current_doc_files() -> list[Path]:
    files: list[Path] = []
    for root in CURRENT_DOC_ROOTS:
        if root.is_file():
            candidates = [root]
        else:
            candidates = [path for path in root.rglob("*") if path.is_file()]
        for path in candidates:
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if any(is_relative_to(path, historical) for historical in HISTORICAL_DOC_PREFIXES):
                continue
            files.append(path)
    return sorted(set(files))


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
