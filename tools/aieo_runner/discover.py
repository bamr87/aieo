"""Discover markdown files under a root by glob and/or git range."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable, List, Set


DEFAULT_IGNORE_DIR_NAMES: Set[str] = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    ".tox",
    "dist",
    "build",
    ".eggs",
}


def _path_has_ignored_dir(path: Path, root: Path, ignore_names: Set[str]) -> bool:
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        return True
    return bool(set(rel.parts) & ignore_names)


def discover_files(
    root: Path,
    globs: List[str],
    ignore_dir_names: Iterable[str] | None = None,
) -> List[Path]:
    """Return sorted unique markdown files matching any glob under root."""
    root = root.resolve()
    ignores = set(ignore_dir_names) if ignore_dir_names is not None else set(DEFAULT_IGNORE_DIR_NAMES)
    seen: Set[Path] = set()
    out: List[Path] = []
    for pattern in globs:
        for p in root.glob(pattern):
            if not p.is_file():
                continue
            if p.suffix.lower() != ".md":
                continue
            if _path_has_ignored_dir(p, root, ignores):
                continue
            rp = p.resolve()
            if rp not in seen:
                seen.add(rp)
                out.append(rp)
    out.sort(key=lambda x: str(x))
    return out


def discover_git_diff_paths(root: Path, base_ref: str, suffix: str = ".md") -> List[Path]:
    """List paths changed between base_ref and HEAD, filtered by suffix (default .md)."""
    root = root.resolve()
    proc = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git diff failed (exit {proc.returncode}): {proc.stderr.strip() or proc.stdout}"
        )
    paths: List[Path] = []
    for line in proc.stdout.splitlines():
        name = line.strip()
        if not name or not name.endswith(suffix):
            continue
        p = (root / name).resolve()
        if p.is_file():
            paths.append(p)
    paths.sort(key=lambda x: str(x))
    return paths


def safe_relative(path: Path, root: Path) -> str:
    """Return POSIX relative path from root; raise if outside root."""
    path = path.resolve()
    root = root.resolve()
    rel = path.relative_to(root)
    return rel.as_posix()
