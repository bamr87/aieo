from pathlib import Path

import pytest

from app.services.workspace_service import WorkspaceService


def test_workspace_init_and_read_write(tmp_path: Path):
    svc = WorkspaceService(tmp_path / ".aieo-workspace")
    init = svc.initialize()
    assert "workspace_root" in init
    tree = svc.list_tree()
    assert any(node.path == "context/brand-voice.md" for node in tree)

    svc.write_file("topics/test-topic.md", "# Test\n")
    res = svc.read_file("topics/test-topic.md")
    assert "Test" in res["content"]


def test_workspace_move(tmp_path: Path):
    svc = WorkspaceService(tmp_path / ".aieo-workspace")
    svc.initialize()
    svc.write_file("drafts/a.md", "hello")
    moved = svc.move_file("drafts/a.md", "published/a.md")
    assert moved["destination"] == "published/a.md"


def test_workspace_rejects_path_traversal(tmp_path: Path):
    svc = WorkspaceService(tmp_path / ".aieo-workspace")
    svc.initialize()
    # Escape via ".." must be rejected, not written outside the root.
    with pytest.raises(ValueError):
        svc.write_file("../escaped.md", "nope")
    assert not (tmp_path / "escaped.md").exists()


def test_workspace_rejects_sibling_prefix_dir(tmp_path: Path):
    # A sibling dir sharing the root's name prefix must not be treated as inside.
    root = tmp_path / "ws"
    svc = WorkspaceService(root)
    svc.initialize()
    with pytest.raises(ValueError):
        svc.read_file("../ws-evil/secret.md")
