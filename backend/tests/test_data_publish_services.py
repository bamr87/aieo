import pytest
import os

os.environ["AIEO_HEADLESS"] = "1"

from app.services.data_service import DataService
from app.services.publish_service import PublishService
from app.services.workspace_service import WorkspaceService


def test_data_service_mock_paths():
    svc = DataService()
    assert "source" in svc.get_ga_top_pages()
    assert "source" in svc.get_gsc_queries()
    assert "source" in svc.get_dfs_serp("test")


@pytest.mark.asyncio
async def test_publish_service_unconfigured(tmp_path):
    ws = WorkspaceService(tmp_path / ".aieo-workspace")
    ws.initialize()
    ws.write_file("drafts/test.md", "# Title")
    publish = PublishService(workspace=ws)
    res = await publish.publish_wordpress("drafts/test.md", title="Title")
    assert res["published"] is False
