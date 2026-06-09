"""Tests for tools.aieo_runner file discovery (no API calls)."""

import sys
from pathlib import Path

# Repo root (…/aieo)
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.aieo_runner.discover import discover_files, safe_relative  # noqa: E402
from tools.aieo_runner.report import write_report_md  # noqa: E402


def test_discover_files_respects_ignore(tmp_path: Path):
    (tmp_path / "a.md").write_text("# a", encoding="utf-8")
    nested = tmp_path / "node_modules" / "pkg"
    nested.mkdir(parents=True)
    (nested / "b.md").write_text("# b", encoding="utf-8")
    found = discover_files(tmp_path, ["**/*.md"], ignore_dir_names={"node_modules"})
    assert len(found) == 1
    assert found[0].name == "a.md"


def test_discover_files_non_md_excluded(tmp_path: Path):
    (tmp_path / "x.md").write_text("x", encoding="utf-8")
    (tmp_path / "y.txt").write_text("y", encoding="utf-8")
    found = discover_files(tmp_path, ["**/*"], ignore_dir_names=set())
    assert len(found) == 1


def test_safe_relative(tmp_path: Path):
    sub = tmp_path / "docs" / "page.md"
    sub.parent.mkdir(parents=True)
    sub.write_text("hi", encoding="utf-8")
    assert safe_relative(sub, tmp_path) == "docs/page.md"


def test_write_report_md(tmp_path: Path):
    rows = [
        {
            "file": "docs/a.md",
            "status": "success",
            "score": 42,
            "grade": "C",
            "gap_count": 3,
            "method": "heuristic",
            "error": None,
            "notes": "",
        }
    ]
    p = write_report_md(tmp_path, rows)
    assert p.is_file()
    text = p.read_text(encoding="utf-8")
    assert "docs/a.md" in text
    assert "heuristic" in text
