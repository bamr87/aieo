#!/usr/bin/env python3
"""Quick test: capture screenshot + run vision-enabled scoring."""

import base64
import json
import os
import ssl
import sys
from pathlib import Path

import httpx

from app.services.scoring_engine import ScoringEngine
from app.services.screenshot_service import ScreenshotService

url = "https://example.com"
out = Path("/app/reports")
out.mkdir(exist_ok=True)

# Step 1: Screenshot
print("=== Testing screenshot capture ===")
ss = ScreenshotService()
ss_result = ss.capture(url)
if "error" in ss_result:
    print(f"Screenshot error: {ss_result['error']}")
    screenshot_b64 = None
else:
    screenshot_b64 = ss_result.get("screenshot_b64")
    print(f"Screenshot: {ss_result['viewport_width']}x{ss_result['viewport_height']}, b64 len={len(screenshot_b64 or '')}")
    out.joinpath("example_com.png").write_bytes(base64.b64decode(screenshot_b64))
    print("Saved: /app/reports/example_com.png")

# Step 2: Fetch HTML + score with screenshot
print("\n=== Testing scoring with screenshot ===")
with httpx.Client(timeout=30, follow_redirects=True, verify=ssl.create_default_context()) as client:
    resp = client.get(url, headers={"User-Agent": "AIEO-Bot/1.0"})
    html = resp.text

engine = ScoringEngine()
result = engine.score(html, format="html", screenshot_b64=screenshot_b64)
print(f"Score: {result['score']}/100  Grade: {result['grade']}  Method: {result['scoring_method']}")

va = result.get("visual_analysis", {})
if va:
    print(f"Visual Analysis: design_score={va.get('design_score')}, fields={list(va.keys())}")
else:
    print("No visual_analysis in response (model may not have returned it)")

# Save result
out.joinpath("example_com.json").write_text(json.dumps(result, indent=2, default=str))
print(f"\nFull result saved to /app/reports/example_com.json")
