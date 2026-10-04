"""Tunable configuration for a PRD-lineage build."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, List, Optional, Tuple

SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        "dist",
        "build",
        ".cache",
        ".aieo-workspace",
        ".tox",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "coverage",
        "htmlcov",
        "vendor",
        "target",
        ".next",
        ".nuxt",
        "eggs",
        ".eggs",
        ".idea",
        ".vscode",
    }
)

SKIP_FILE_NAMES = frozenset(
    {
        ".env",
        ".env.local",
        ".env.production",
        ".env.development",
        "id_rsa",
        "id_ed25519",
    }
)

SKIP_SUFFIXES = frozenset(
    {".pem", ".key", ".p12", ".pfx", ".der", ".crt", ".p8", ".kdbx"}
)

TEXT_SUFFIXES = frozenset({".md", ".markdown", ".rst", ".txt", ".adoc"})

MANIFEST_NAMES = frozenset(
    {
        "pyproject.toml",
        "package.json",
        "setup.cfg",
        "setup.py",
        "cargo.toml",
        "go.mod",
        "composer.json",
        "gemspec",
    }
)


@dataclass
class PrdConfig:
    max_files: int = 400
    max_bytes_per_file: int = 256 * 1024
    max_text_chars: int = 20000
    skip_dir_names: Tuple[str, ...] = field(
        default_factory=lambda: tuple(sorted(SKIP_DIR_NAMES))
    )
    agent_enabled: bool = True
    agent_model: Optional[str] = None
    agent_max_sources: int = 12
    agent_timeout: int = 180
    agent_synthesis: bool = True
    agent_max_chars: int = 6000
    formats: Optional[List[str]] = None

    def __post_init__(self) -> None:
        self.max_files = max(1, int(self.max_files))
        self.max_bytes_per_file = max(1024, int(self.max_bytes_per_file))

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "PrdConfig":
        if not data:
            return cls()
        known = {f.name for f in fields(cls)}
        kwargs = {k: v for k, v in data.items() if k in known and v is not None}
        return cls(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
