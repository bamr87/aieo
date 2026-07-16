"""AIEO MCP (Model Context Protocol) tool server.

Exposes the AIEO scoring engine as MCP tools that AI agents and
other MCP clients can invoke. This makes the scoring engine composable
with any MCP-compatible AI workflow.

Usage:
    python -m backend.app.mcp_server
    # or via the MCP config in mcp_config.json

Tools exposed:
    - aieo_score_content: Score raw content against AIEO patterns
    - aieo_audit_url: Fetch a URL and score its content
    - aieo_list_patterns: List all scoring patterns and their weights
    - aieo_get_pattern: Get detailed definition of a specific pattern
"""

# Imports are intentionally split around runtime setup (path/env) below.
# ruff: noqa: E402

import json
import logging
import ssl
import sys
import os

# Ensure backend is importable when run as a module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP SDK not installed. Install with: pip install mcp")

from app.services.scoring_engine import ScoringEngine
from app.services.prompt_loader import PromptLoader
from app.services.agent_runner import AgentRunner
from app.services.analyze_existing_service import AnalyzeExistingService
from app.services.landing_service import LandingService
from app.services.priorities_service import PrioritiesService
from app.services.publish_service import PublishService
from app.services.research_service import ResearchService
from app.services.rewrite_service import RewriteService
from app.services.scrub_service import ScrubService
from app.services.workspace_service import WorkspaceService
from app.services.write_service import WriteService
from app.services.site_snapshot import CrawlConfig, SiteSnapshotService
from app.core.config import workspace_root


def create_mcp_server():
    """Create and configure the AIEO MCP server."""
    if not MCP_AVAILABLE:
        raise ImportError("MCP SDK required. Install with: pip install mcp")

    server = Server("aieo-scoring")
    engine = ScoringEngine()
    loader = PromptLoader()
    research_service = ResearchService()
    write_service = WriteService()
    rewrite_service = RewriteService()
    analyze_existing_service = AnalyzeExistingService()
    scrub_service = ScrubService()
    priorities_service = PrioritiesService()
    landing_service = LandingService()
    publish_service = PublishService()
    agent_runner = AgentRunner()
    workspace_service = WorkspaceService(workspace_root())
    snapshot_service = SiteSnapshotService()

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="aieo_score_content",
                description=(
                    "Score content against AIEO (AI Engine Optimization) patterns. "
                    "Returns a 0-100 score, letter grade, per-pattern breakdown with "
                    "evidence and recommendations, gap analysis, and anti-pattern detection."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The content to score (markdown or HTML).",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["markdown", "html"],
                            "default": "markdown",
                            "description": "Content format.",
                        },
                    },
                    "required": ["content"],
                },
            ),
            Tool(
                name="aieo_audit_url",
                description=(
                    "Fetch a URL and score its content against AIEO patterns. "
                    "Returns the same scoring result as aieo_score_content."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL to fetch and score.",
                        },
                    },
                    "required": ["url"],
                },
            ),
            Tool(
                name="aieo_list_patterns",
                description=(
                    "List all AIEO scoring patterns with their names, weights, and max scores. "
                    "Use this to understand what the scoring engine evaluates."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="aieo_get_pattern",
                description=(
                    "Get the full definition of a specific AIEO scoring pattern, "
                    "including scoring criteria, examples, and context sensitivity notes."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pattern_name": {
                            "type": "string",
                            "description": "Name of the pattern (e.g., 'structured_data', 'entity_density').",
                        },
                    },
                    "required": ["pattern_name"],
                },
            ),
            Tool(
                name="aieo_research",
                description="Create a research brief for a topic.",
                inputSchema={
                    "type": "object",
                    "properties": {"topic": {"type": "string"}},
                    "required": ["topic"],
                },
            ),
            Tool(
                name="aieo_write",
                description="Write a long-form draft for a topic.",
                inputSchema={
                    "type": "object",
                    "properties": {"topic": {"type": "string"}},
                    "required": ["topic"],
                },
            ),
            Tool(
                name="aieo_rewrite",
                description="Rewrite an existing workspace file.",
                inputSchema={
                    "type": "object",
                    "properties": {"source_path": {"type": "string"}},
                    "required": ["source_path"],
                },
            ),
            Tool(
                name="aieo_analyze_existing",
                description="Analyze existing content URL or file.",
                inputSchema={
                    "type": "object",
                    "properties": {"target": {"type": "string"}},
                    "required": ["target"],
                },
            ),
            Tool(
                name="aieo_scrub",
                description="Remove AI-style artifacts from content.",
                inputSchema={
                    "type": "object",
                    "properties": {"content": {"type": "string"}},
                    "required": ["content"],
                },
            ),
            Tool(
                name="aieo_editor_review",
                description="Run the editor agent on content.",
                inputSchema={
                    "type": "object",
                    "properties": {"content": {"type": "string"}},
                    "required": ["content"],
                },
            ),
            Tool(
                name="aieo_headline_generate",
                description="Run headline-generator agent for a topic.",
                inputSchema={
                    "type": "object",
                    "properties": {"topic": {"type": "string"}},
                    "required": ["topic"],
                },
            ),
            Tool(
                name="aieo_priorities",
                description="Build content priority queue from performance signals.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="aieo_landing_audit",
                description="Audit landing page content for CRO quality.",
                inputSchema={
                    "type": "object",
                    "properties": {"content": {"type": "string"}},
                    "required": ["content"],
                },
            ),
            Tool(
                name="aieo_readability",
                description="Get readability dimension for content.",
                inputSchema={
                    "type": "object",
                    "properties": {"content": {"type": "string"}},
                    "required": ["content"],
                },
            ),
            Tool(
                name="aieo_keyword_analysis",
                description="Get keyword analysis for content.",
                inputSchema={
                    "type": "object",
                    "properties": {"content": {"type": "string"}},
                    "required": ["content"],
                },
            ),
            Tool(
                name="aieo_search_intent",
                description="Infer search intent from content/query.",
                inputSchema={
                    "type": "object",
                    "properties": {"content": {"type": "string"}},
                    "required": ["content"],
                },
            ),
            Tool(
                name="aieo_publish_wordpress",
                description="Publish a draft path to WordPress.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "draft_path": {"type": "string"},
                        "title": {"type": "string"},
                    },
                    "required": ["draft_path", "title"],
                },
            ),
            Tool(
                name="aieo_workspace_list",
                description="List workspace files and directories.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="aieo_workspace_read",
                description="Read one workspace file.",
                inputSchema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            ),
            Tool(
                name="aieo_workspace_write",
                description="Write one workspace file.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            ),
            Tool(
                name="aieo_crawl_site",
                description=(
                    "Crawl a Jekyll/static site into a cached, offline, multi-format "
                    "snapshot (text/json/markdown/html/pdf/bundle). Discovers pages via "
                    "sitemap.xml/feed.xml/robots.txt and link-following, caches every "
                    "page so re-runs only re-fetch changed pages, and writes single-file "
                    "exports. Returns a manifest with stats and output paths."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "base_url": {"type": "string"},
                        "formats": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "text",
                                    "json",
                                    "markdown",
                                    "html",
                                    "pdf",
                                    "bundle",
                                ],
                            },
                        },
                        "max_pages": {"type": "integer", "default": 200},
                        "max_depth": {"type": "integer", "default": 6},
                        "max_link_pages": {"type": "integer", "default": 200},
                        "delay_seconds": {"type": "number", "default": 0.25},
                        "ttl_seconds": {"type": "integer", "default": 0},
                        "respect_robots": {"type": "boolean", "default": True},
                        "use_cache": {"type": "boolean", "default": True},
                        "include_external": {"type": "boolean", "default": False},
                        "include_assets": {"type": "boolean", "default": False},
                        "strip_boilerplate": {"type": "boolean", "default": True},
                        "refresh": {"type": "boolean", "default": False},
                    },
                    "required": ["base_url"],
                },
            ),
            Tool(
                name="aieo_crawl_manifest",
                description=(
                    "Return the most recent cached snapshot manifest for a site slug "
                    "(e.g. 'bashconsultants_com') without re-crawling."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {"site_slug": {"type": "string"}},
                    "required": ["site_slug"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        try:
            return await _dispatch_tool(name, arguments)
        except Exception as exc:
            logger.exception("MCP tool %s failed", name)
            return [
                TextContent(
                    type="text", text=json.dumps({"error": str(exc), "tool": name})
                )
            ]

    async def _dispatch_tool(name: str, arguments: dict):
        if name == "aieo_score_content":
            content = arguments.get("content", "")
            fmt = arguments.get("format", "markdown")
            result = engine.score(content, format=fmt)
            return [
                TextContent(type="text", text=json.dumps(result, indent=2, default=str))
            ]

        elif name == "aieo_audit_url":
            url = arguments.get("url", "")
            if not url.startswith(("http://", "https://")):
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {"error": "URL must start with http:// or https://"}
                        ),
                    )
                ]
            try:
                import httpx

                with httpx.Client(
                    timeout=30.0,
                    follow_redirects=True,
                    verify=ssl.create_default_context(),
                ) as client:
                    resp = client.get(url, headers={"User-Agent": "AIEO-Bot/1.0"})
                    resp.raise_for_status()
                    html = resp.text

                # Capture screenshot for visual analysis
                screenshot_b64 = None
                try:
                    from app.services.screenshot_service import ScreenshotService

                    ss = ScreenshotService()
                    ss_result = await ss.capture_async(url)
                    if "error" not in ss_result:
                        screenshot_b64 = ss_result.get("screenshot_b64")
                        logger.info(
                            "Screenshot captured for %s (%dx%d)",
                            url,
                            ss_result.get("viewport_width", 0),
                            ss_result.get("viewport_height", 0),
                        )
                    else:
                        logger.warning(
                            "Screenshot skipped for %s: %s", url, ss_result["error"]
                        )
                except Exception as e:
                    logger.warning("Screenshot capture failed for %s: %s", url, e)

                result = engine.score(
                    html, format="html", screenshot_b64=screenshot_b64
                )
                result["url"] = url
                if screenshot_b64:
                    result["screenshot_b64"] = screenshot_b64
                return [
                    TextContent(
                        type="text", text=json.dumps(result, indent=2, default=str)
                    )
                ]
            except Exception as e:
                return [
                    TextContent(
                        type="text", text=json.dumps({"error": str(e), "url": url})
                    )
                ]

        elif name == "aieo_list_patterns":
            patterns = loader.load_patterns()
            summary = [
                {
                    "name": p["name"],
                    "display_name": p["display_name"],
                    "weight": p["weight"],
                    "max_score": p["max_score"],
                }
                for p in patterns
            ]
            return [TextContent(type="text", text=json.dumps(summary, indent=2))]

        elif name == "aieo_get_pattern":
            pattern_name = arguments.get("pattern_name", "")
            patterns = loader.load_patterns()
            match = next((p for p in patterns if p["name"] == pattern_name), None)
            if match:
                return [TextContent(type="text", text=json.dumps(match, indent=2))]
            else:
                available = [p["name"] for p in patterns]
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "error": f"Pattern '{pattern_name}' not found",
                                "available": available,
                            }
                        ),
                    )
                ]

        elif name == "aieo_research":
            result = await research_service.create_brief(arguments.get("topic", ""))
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        elif name == "aieo_write":
            result = await write_service.write(arguments.get("topic", ""))
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        elif name == "aieo_rewrite":
            result = await rewrite_service.rewrite(arguments.get("source_path", ""))
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        elif name == "aieo_analyze_existing":
            result = await analyze_existing_service.analyze(arguments.get("target", ""))
            return [
                TextContent(type="text", text=json.dumps(result, indent=2, default=str))
            ]
        elif name == "aieo_scrub":
            result = await scrub_service.scrub(arguments.get("content", ""))
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        elif name == "aieo_editor_review":
            result = await agent_runner.run_agent(
                "editor", arguments.get("content", "")
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        elif name == "aieo_headline_generate":
            topic = arguments.get("topic", "")
            result = await agent_runner.run_agent(
                "headline-generator", topic, extra_inputs={"topic": topic}
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        elif name == "aieo_priorities":
            return [
                TextContent(
                    type="text",
                    text=json.dumps(priorities_service.build_priorities(), indent=2),
                )
            ]
        elif name == "aieo_landing_audit":
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        landing_service.audit(arguments.get("content", "")), indent=2
                    ),
                )
            ]
        elif name == "aieo_readability":
            result = engine.score(arguments.get("content", ""), format="markdown")
            return [
                TextContent(
                    type="text",
                    text=json.dumps(result.get("readability", {}), indent=2),
                )
            ]
        elif name == "aieo_keyword_analysis":
            result = engine.score(arguments.get("content", ""), format="markdown")
            return [
                TextContent(
                    type="text",
                    text=json.dumps(result.get("keyword_analysis", {}), indent=2),
                )
            ]
        elif name == "aieo_search_intent":
            result = engine.score(arguments.get("content", ""), format="markdown")
            return [
                TextContent(
                    type="text",
                    text=json.dumps(result.get("search_intent", {}), indent=2),
                )
            ]
        elif name == "aieo_publish_wordpress":
            result = await publish_service.publish_wordpress(
                draft_path=arguments.get("draft_path", ""),
                title=arguments.get("title", ""),
                metadata=arguments.get("metadata", {}),
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        elif name == "aieo_workspace_list":
            workspace_service.initialize()
            nodes = [node.__dict__ for node in workspace_service.list_tree()]
            return [
                TextContent(type="text", text=json.dumps({"nodes": nodes}, indent=2))
            ]
        elif name == "aieo_workspace_read":
            result = workspace_service.read_file(arguments.get("path", ""))
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        elif name == "aieo_workspace_write":
            workspace_service.write_file(
                arguments.get("path", ""), arguments.get("content", "")
            )
            return [TextContent(type="text", text=json.dumps({"ok": True}, indent=2))]
        elif name == "aieo_crawl_site":
            import anyio

            base_url = arguments.get("base_url", "")
            if not base_url:
                return [
                    TextContent(
                        type="text", text=json.dumps({"error": "base_url required"})
                    )
                ]
            cfg = CrawlConfig.from_dict(arguments)
            formats = arguments.get("formats")
            # Crawl is synchronous, blocking I/O — run it off the event loop.
            result = await anyio.to_thread.run_sync(
                lambda: snapshot_service.snapshot(base_url, formats=formats, cfg=cfg)
            )
            return [
                TextContent(type="text", text=json.dumps(result, indent=2, default=str))
            ]
        elif name == "aieo_crawl_manifest":
            manifest = snapshot_service.load_manifest(arguments.get("site_slug", ""))
            if manifest is None:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "error": "no snapshot found",
                                "site_slug": arguments.get("site_slug"),
                            }
                        ),
                    )
                ]
            return [
                TextContent(
                    type="text", text=json.dumps(manifest, indent=2, default=str)
                )
            ]

        return [
            TextContent(
                type="text", text=json.dumps({"error": f"Unknown tool: {name}"})
            )
        ]

    return server


async def main():
    """Run the MCP server on stdio."""
    server = create_mcp_server()
    async with stdio_server() as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
