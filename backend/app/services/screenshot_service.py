"""Screenshot capture service for AIEO site analysis.

Uses Playwright to render pages in a headless browser and capture
full-page and viewport screenshots for visual AI analysis.
"""

import base64
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ScreenshotService:
    """Capture website screenshots using Playwright."""

    def __init__(self, viewport_width: int = 1280, viewport_height: int = 800):
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height

    def capture(
        self,
        url: str,
        output_dir: Optional[Path] = None,
        filename: Optional[str] = None,
        full_page: bool = True,
    ) -> dict:
        """Capture a screenshot of a URL.

        Args:
            url: The URL to screenshot.
            output_dir: Directory to save the PNG file (optional).
            filename: Base filename without extension (optional).
            full_page: Whether to capture the full scrollable page.

        Returns:
            Dict with keys:
                - screenshot_b64: Base64-encoded PNG data
                - screenshot_path: Path to saved file (if output_dir provided)
                - viewport_width, viewport_height: Dimensions used
                - full_page: Whether full page was captured
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning(
                "Playwright not installed. Install with: pip install playwright && playwright install chromium"
            )
            return {"error": "playwright not available"}

        result = {
            "viewport_width": self.viewport_width,
            "viewport_height": self.viewport_height,
            "full_page": full_page,
        }

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={
                        "width": self.viewport_width,
                        "height": self.viewport_height,
                    },
                    user_agent="AIEO-Bot/1.0 (screenshot)",
                )
                page = context.new_page()

                # Navigate with timeout
                page.goto(url, wait_until="networkidle", timeout=30000)

                # Wait a moment for lazy-loaded content
                page.wait_for_timeout(1000)

                # Capture screenshot as bytes
                screenshot_bytes = page.screenshot(full_page=full_page, type="png")

                # Encode to base64 for AI API transmission
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
                result["screenshot_b64"] = screenshot_b64

                # Save to file if output_dir provided
                if output_dir and filename:
                    out_path = Path(output_dir)
                    out_path.mkdir(parents=True, exist_ok=True)
                    screenshot_path = out_path / f"{filename}.png"
                    screenshot_path.write_bytes(screenshot_bytes)
                    result["screenshot_path"] = str(screenshot_path)
                    logger.info("Screenshot saved: %s", screenshot_path)

                browser.close()

        except Exception as e:
            logger.warning("Screenshot capture failed for %s: %s", url, e)
            result["error"] = str(e)

        return result

    async def capture_async(
        self,
        url: str,
        output_dir: Optional[Path] = None,
        filename: Optional[str] = None,
        full_page: bool = True,
    ) -> dict:
        """Async version of capture(), for use inside an async event loop (e.g. MCP server).

        Same args and return value as capture().
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("Playwright not installed.")
            return {"error": "playwright not available"}

        result = {
            "viewport_width": self.viewport_width,
            "viewport_height": self.viewport_height,
            "full_page": full_page,
        }

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={
                        "width": self.viewport_width,
                        "height": self.viewport_height,
                    },
                    user_agent="AIEO-Bot/1.0 (screenshot)",
                )
                page = await context.new_page()

                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(1000)

                screenshot_bytes = await page.screenshot(
                    full_page=full_page, type="png"
                )
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
                result["screenshot_b64"] = screenshot_b64

                if output_dir and filename:
                    out_path = Path(output_dir)
                    out_path.mkdir(parents=True, exist_ok=True)
                    screenshot_path = out_path / f"{filename}.png"
                    screenshot_path.write_bytes(screenshot_bytes)
                    result["screenshot_path"] = str(screenshot_path)
                    logger.info("Screenshot saved: %s", screenshot_path)

                await browser.close()

        except Exception as e:
            logger.warning("Screenshot capture failed for %s: %s", url, e)
            result["error"] = str(e)

        return result
