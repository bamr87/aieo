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


def create_mcp_server():
    """Create and configure the AIEO MCP server."""
    if not MCP_AVAILABLE:
        raise ImportError("MCP SDK required. Install with: pip install mcp")

    server = Server("aieo-scoring")
    engine = ScoringEngine()
    loader = PromptLoader()

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
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == "aieo_score_content":
            content = arguments.get("content", "")
            fmt = arguments.get("format", "markdown")
            result = engine.score(content, format=fmt)
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

        elif name == "aieo_audit_url":
            url = arguments.get("url", "")
            if not url.startswith(("http://", "https://")):
                return [TextContent(type="text", text=json.dumps({"error": "URL must start with http:// or https://"}))]
            try:
                import httpx
                with httpx.Client(timeout=30.0, follow_redirects=True, verify=ssl.create_default_context()) as client:
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
                        logger.info("Screenshot captured for %s (%dx%d)", url,
                                    ss_result.get("viewport_width", 0), ss_result.get("viewport_height", 0))
                    else:
                        logger.warning("Screenshot skipped for %s: %s", url, ss_result["error"])
                except Exception as e:
                    logger.warning("Screenshot capture failed for %s: %s", url, e)

                result = engine.score(html, format="html", screenshot_b64=screenshot_b64)
                result["url"] = url
                if screenshot_b64:
                    result["screenshot_b64"] = screenshot_b64
                return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e), "url": url}))]

        elif name == "aieo_list_patterns":
            patterns = loader.load_patterns()
            summary = [
                {"name": p["name"], "display_name": p["display_name"],
                 "weight": p["weight"], "max_score": p["max_score"]}
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
                return [TextContent(type="text", text=json.dumps(
                    {"error": f"Pattern '{pattern_name}' not found", "available": available}
                ))]

        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

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
