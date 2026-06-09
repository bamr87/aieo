"""Content lifecycle API endpoints."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import verify_api_key_simple as verify_api_key
from ...services.agent_runner import AgentRunner
from ...services.analyze_existing_service import AnalyzeExistingService
from ...services.data_service import DataService
from ...services.landing_service import LandingService
from ...services.priorities_service import PrioritiesService
from ...services.publish_service import PublishService
from ...services.research_service import ResearchService
from ...services.rewrite_service import RewriteService
from ...services.scrub_service import ScrubService
from ...services.write_service import WriteService


router = APIRouter()
research_service = ResearchService()
write_service = WriteService()
rewrite_service = RewriteService()
analyze_existing_service = AnalyzeExistingService()
scrub_service = ScrubService()
priorities_service = PrioritiesService()
landing_service = LandingService()
data_service = DataService()
publish_service = PublishService()
agent_runner = AgentRunner()


class TopicRequest(BaseModel):
    topic: str
    model: Optional[str] = None


class WriteRequest(BaseModel):
    topic: str
    brief_path: Optional[str] = None
    model: Optional[str] = None


class RewriteRequest(BaseModel):
    source_path: str
    model: Optional[str] = None


class AnalyzeExistingRequest(BaseModel):
    target: str
    model: Optional[str] = None


class ScrubRequest(BaseModel):
    content: str
    model: Optional[str] = None


class AgentRequest(BaseModel):
    agent_name: str
    content: str
    extra_inputs: Optional[Dict[str, Any]] = None
    model: Optional[str] = None


class LandingAuditRequest(BaseModel):
    content: str


class LandingCompetitorRequest(BaseModel):
    url: str
    model: Optional[str] = None


class DataForSEORequest(BaseModel):
    keyword: str


class PublishWordpressRequest(BaseModel):
    draft_path: str
    title: str
    metadata: Optional[Dict[str, Any]] = None


@router.post("/aieo/research")
async def research(
    request: TopicRequest,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    return await research_service.create_brief(request.topic, model=request.model)


@router.post("/aieo/write")
async def write(
    request: WriteRequest,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    return await write_service.write(request.topic, brief_path=request.brief_path, model=request.model)


@router.post("/aieo/rewrite")
async def rewrite(
    request: RewriteRequest,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    try:
        return await rewrite_service.rewrite(request.source_path, model=request.model)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/aieo/analyze-existing")
async def analyze_existing(
    request: AnalyzeExistingRequest,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    return await analyze_existing_service.analyze(request.target, model=request.model)


@router.post("/aieo/scrub")
async def scrub(
    request: ScrubRequest,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    return await scrub_service.scrub(request.content, model=request.model)


@router.get("/aieo/priorities")
async def priorities(
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    return priorities_service.build_priorities()


@router.post("/aieo/agent/run")
async def run_agent(
    request: AgentRequest,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    return await agent_runner.run_agent(
        request.agent_name,
        request.content,
        extra_inputs=request.extra_inputs,
        model=request.model,
    )


@router.post("/aieo/landing/write")
async def landing_write(
    request: TopicRequest,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    return await landing_service.write(request.topic, model=request.model)


@router.post("/aieo/landing/audit")
async def landing_audit(
    request: LandingAuditRequest,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    return landing_service.audit(request.content)


@router.post("/aieo/landing/research")
async def landing_research(
    request: TopicRequest,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    return await landing_service.research(request.topic, model=request.model)


@router.post("/aieo/landing/competitor")
async def landing_competitor(
    request: LandingCompetitorRequest,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    return await landing_service.competitor(request.url, model=request.model)


@router.get("/aieo/data/ga/top-pages")
async def data_ga(
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    return data_service.get_ga_top_pages()


@router.get("/aieo/data/gsc/queries")
async def data_gsc(
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    return data_service.get_gsc_queries()


@router.post("/aieo/data/dfs/serp")
async def data_dfs(
    request: DataForSEORequest,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    return data_service.get_dfs_serp(request.keyword)


@router.post("/aieo/publish/wordpress")
async def publish_wordpress(
    request: PublishWordpressRequest,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    del api_key, db
    return await publish_service.publish_wordpress(
        draft_path=request.draft_path,
        title=request.title,
        metadata=request.metadata or {},
    )
