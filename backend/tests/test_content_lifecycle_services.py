import pytest
import os

os.environ["AIEO_HEADLESS"] = "1"

from app.services.ai_service import AIService
from app.services.research_service import ResearchService
from app.services.rewrite_service import RewriteService
from app.services.scrub_service import ScrubService
from app.services.workspace_service import WorkspaceService
from app.services.write_service import WriteService


class FakeAI(AIService):
    async def generate(self, prompt: str, model: str | None = None) -> str:
        return "# Generated\n\nTest content.\n"


@pytest.mark.asyncio
async def test_research_write_rewrite_scrub(tmp_path):
    ws = WorkspaceService(tmp_path / ".aieo-workspace")
    ws.initialize()
    ai = FakeAI()

    research = ResearchService(ai_service=ai, workspace=ws)
    brief = await research.create_brief("Test Topic")
    assert brief["path"].startswith("research/")

    writer = WriteService(ai_service=ai, workspace=ws)
    draft = await writer.write("Test Topic", brief_path=brief["path"])
    assert draft["path"].startswith("drafts/")

    rewrite = RewriteService(ai_service=ai, workspace=ws)
    rewrite_out = await rewrite.rewrite(draft["path"])
    assert rewrite_out["path"].startswith("rewrites/")

    scrub = ScrubService(ai_service=ai, workspace=ws)
    scrub_out = await scrub.scrub("hello")
    assert scrub_out["path"].startswith("drafts/scrubbed-")
