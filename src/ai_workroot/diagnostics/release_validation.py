"""Package-owned release surface validation helpers."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess


PRIVATE_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?im)(^|[,{])\s*['\"]?(api[_-]?key|secret|password|token)['\"]?\s*[:=]\s*['\"]?[^'\"\s,}]+"),
]
GENERATED_SUFFIXES = {
    ".sqlite",
    ".sqlite3",
    ".db",
    ".duckdb",
    ".wal",
}
GENERATED_STATE_PATH_PREFIXES = {
    ".ai-workroot-local/",
    "cache/",
    "context/debug/",
    "global-cache/",
    "logs/",
}


def add_error(errors: list[str], message: str) -> None:
    errors.append(message)


def is_git_ignored(root: Path, path: Path) -> bool:
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        return False
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", rel],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def validate_release_surface(root: Path, errors: list[str]) -> None:
    root = root.expanduser().resolve()
    release_paths = _release_surface_paths(root)
    for path in release_paths:
        if not path.exists():
            continue
        if path.is_file() and path.suffix.lower() in GENERATED_SUFFIXES:
            add_error(errors, f"generated store must not be committed for release: {path.relative_to(root).as_posix()}")
        rel = path.relative_to(root).as_posix()
        if path.is_file() and any(rel.startswith(prefix) for prefix in GENERATED_STATE_PATH_PREFIXES):
            add_error(errors, f"generated managed state path must not be committed for release: {rel}")
        if path.is_file() and rel.startswith(".workroot/runtime/cache/") and path.name != ".gitkeep":
            add_error(errors, f"retired Public Seed generated runtime cache must not be present for release: {rel}")
        if path.is_file() and rel.startswith(".workroot/runtime/logs/") and path.name != ".gitkeep":
            add_error(errors, f"retired Public Seed generated runtime log must not be present for release: {rel}")
        if path.name in {".DS_Store"} or ".idea" in path.parts or "__pycache__" in path.parts:
            add_error(errors, f"local metadata must not be committed: {path.relative_to(root).as_posix()}")

    text_exts = {".md", ".json", ".csv", ".py", ".yml", ".yaml", ".txt", ".sql"}
    for path in release_paths:
        if not path.is_file() or path.suffix.lower() not in text_exts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            add_error(errors, f"text file must be UTF-8: {path.relative_to(root).as_posix()}: {exc}")
            continue
        for pattern in PRIVATE_PATTERNS:
            if pattern.search(text):
                add_error(errors, f"possible private residue in {path.relative_to(root).as_posix()}")
                break


def _release_surface_paths(root: Path) -> list[Path]:
    root = root.expanduser().resolve()
    git_paths = _git_release_surface_paths(root)
    if git_paths is not None:
        return git_paths
    return _filesystem_release_surface_paths(root)


def _git_release_surface_paths(root: Path) -> list[Path] | None:
    tracked = _git_list(root, ("ls-files", "-z"))
    untracked = _git_list(root, ("ls-files", "-z", "--others", "--exclude-standard"))
    if tracked is None or untracked is None:
        return None
    rels = sorted({rel for rel in (*tracked, *untracked) if rel})
    return [root / rel for rel in rels]


def _git_list(root: Path, args: tuple[str, ...]) -> list[str] | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            text=False,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return [item.decode("utf-8", errors="replace") for item in result.stdout.split(b"\0") if item]


def _filesystem_release_surface_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in root.rglob("*"):
        if ".git" in path.parts:
            continue
        if is_git_ignored(root, path):
            continue
        paths.append(path)
    return paths
