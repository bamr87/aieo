"""Offline tests for PRD lineage: map, extract, heuristic analyze, export."""

from __future__ import annotations

import json
from pathlib import Path

from app.services.prd_lineage import PrdConfig, PrdInventory, PrdLineageService
from app.services.prd_lineage import exporters
from app.services.prd_lineage.agent import parse_json
from app.services.prd_lineage.elements import MUST_IDS
from app.services.prd_lineage.mapper import classify
from app.services.prompt_loader import PromptLoader


def _write_repo(root: Path) -> Path:
    repo = root / "widget"
    (repo / "docs").mkdir(parents=True)
    (repo / "node_modules" / "dep").mkdir(parents=True)
    (repo / "PRD.md").write_text(
        """# PRD: Widget Pro
**Version:** 0.9.0

## Problem Statement
Who is affected: indie makers. Pain point: shipping without a spec.
Why now: AI agents need a source of truth. Key hypothesis: a written PRD cuts rework.

## Personas
| Persona | Pain Point | Jobs to Be Done |
| Maker | No spec | Ship a product |

## MVP
P0 Must Have: core editor. Should have: export.

## Out of Scope
Mobile app. We are not building a marketplace.

## Executive Summary
Widget Pro is a tiny product for makers.
""",
        encoding="utf-8",
    )
    (repo / "README.md").write_text(
        """# Widget
Ship faster.

Version 1.2.0
""",
        encoding="utf-8",
    )
    (repo / "CHANGELOG.md").write_text(
        """# Changelog
## [1.2.0] - 2026-01-01
- Added editor
""",
        encoding="utf-8",
    )
    (repo / "CLAUDE.md").write_text(
        "# CLAUDE.md\n\nThis is Widget, a maker tool.\n",
        encoding="utf-8",
    )
    (repo / "docs" / "ARCHITECTURE.md").write_text(
        "# Architecture\n\nSee [the PRD](../PRD.md) for scope.\n",
        encoding="utf-8",
    )
    (repo / "package.json").write_text(
        json.dumps({"name": "widget", "version": "1.2.0", "description": "Maker tool"}),
        encoding="utf-8",
    )
    (repo / "node_modules" / "dep" / "README.md").write_text("# dep\n", encoding="utf-8")
    (repo / ".env").write_text("SECRET=1\n", encoding="utf-8")
    return repo


def test_classify_roles():
    assert classify("PRD-aieo.md") == "canonical_prd"
    assert classify("docs/prd.md") == "canonical_prd"
    assert classify("docs/PRD_LINEAGE.md") == "docs"
    assert classify(".prompts/PRD_IMPROVEMENT_PROMPT.md") == "prompt_spec"
    assert classify("README.md") == "readme"
    assert classify("CLAUDE.md") == "agent_instructions"
    assert classify("package.json") == "packaging"
    assert classify("docs/API.md") == "api"


def test_map_skips_secrets_and_vendor(tmp_path: Path):
    repo = _write_repo(tmp_path)
    inv = PrdLineageService(root=tmp_path / "ws").build(
        str(repo), PrdConfig(agent_enabled=False), map_only=True
    )
    paths = {s.path for s in inv.sources}
    assert "PRD.md" in paths
    assert "README.md" in paths
    assert "package.json" in paths
    assert ".env" not in paths
    assert "node_modules/dep/README.md" not in paths
    roles = {s.path: s.role for s in inv.sources}
    assert roles["PRD.md"] == "canonical_prd"
    assert roles["README.md"] == "readme"
    assert roles["CLAUDE.md"] == "agent_instructions"


def test_extract_elements_and_lineage(tmp_path: Path):
    repo = _write_repo(tmp_path)
    inv = PrdLineageService(root=tmp_path / "ws").build(
        str(repo), PrdConfig(agent_enabled=False)
    )
    prd = inv.canonical
    assert prd is not None
    assert "problem" in prd.element_hits
    assert "mvp" in prd.element_hits
    assert "personas" in prd.element_hits
    assert "oos" in prd.element_hits
    assert "success" not in inv.element_index
    arch = next(s for s in inv.sources if s.path == "docs/ARCHITECTURE.md")
    assert "PRD.md" in arch.outbound
    assert any(e.source == "docs/ARCHITECTURE.md" and e.target == "PRD.md" for e in inv.edges)


def test_heuristic_completeness_and_drift(tmp_path: Path):
    repo = _write_repo(tmp_path)
    inv = PrdLineageService(root=tmp_path / "ws").build(
        str(repo), PrdConfig(agent_enabled=False)
    )
    assert inv.analysis_method == "heuristic"
    analysis = inv.analysis
    assert analysis["canonical_prd"] == "PRD.md"
    assert analysis["maturity"] in ("idea", "draft", "mvp_ready")
    assert "success" in analysis["completeness"]["must_missing"]
    fields = {d["field"] for d in analysis["drift"]}
    assert "product_name" in fields
    assert "version" in fields
    broken_from = {b["from"] for b in analysis["lineage"]["broken"]}
    assert "README.md" in broken_from
    solid_from = {s["from"] for s in analysis["lineage"]["solid"]}
    assert "docs/ARCHITECTURE.md" in solid_from
    assert analysis["completeness"]["score"] < 100
    for el in MUST_IDS:
        assert el in analysis["completeness"]["must_present"] + analysis["completeness"][
            "must_missing"
        ]


def test_map_only_skips_extract(tmp_path: Path):
    repo = _write_repo(tmp_path)
    inv = PrdLineageService(root=tmp_path / "ws").build(
        str(repo), PrdConfig(agent_enabled=False), map_only=True
    )
    assert inv.phases["map"]["sources"] >= 4
    assert "extract" not in inv.phases
    assert all(not s.extracted for s in inv.sources)


def test_run_exports_and_manifest(tmp_path: Path):
    repo = _write_repo(tmp_path)
    ws = tmp_path / "ws"
    result = PrdLineageService(root=ws).run(
        str(repo),
        formats=["json", "markdown", "mermaid"],
        cfg=PrdConfig(agent_enabled=False),
        out_dir=tmp_path / "out",
    )
    assert result["canonical_prd"] == "PRD.md"
    assert Path(result["outputs"]["markdown"]["path"]).exists()
    md = Path(result["outputs"]["markdown"]["path"]).read_text(encoding="utf-8")
    assert "Element coverage" in md
    assert "PRD.md" in md
    loaded = PrdLineageService(root=ws).load_manifest(result["repo_slug"])
    assert loaded is not None
    roundtrip = PrdInventory.from_dict(loaded)
    assert roundtrip.canonical and roundtrip.canonical.path == "PRD.md"
    listed = PrdLineageService(root=ws).list_inventories()
    assert listed and listed[0]["repo_slug"] == result["repo_slug"]


def test_no_prd_repo(tmp_path: Path):
    repo = tmp_path / "bare"
    repo.mkdir()
    (repo / "README.md").write_text("# Bare\nA tool.\n", encoding="utf-8")
    inv = PrdLineageService(root=tmp_path / "ws").build(
        str(repo), PrdConfig(agent_enabled=False)
    )
    assert inv.canonical is None
    assert inv.analysis["maturity"] == "none"
    assert inv.analysis["prd_improvements"]


def test_agent_runner_override(tmp_path: Path):
    repo = _write_repo(tmp_path)

    def runner(*, prompt, payload, model=None):
        data = json.loads(payload) if payload.lstrip().startswith("{") else {}
        if "path" in data:
            return json.dumps(
                {
                    "role": data.get("role"),
                    "is_product_spec": data.get("role") == "canonical_prd",
                    "elements_present": data.get("element_hits") or [],
                    "elements_missing_substance": [],
                    "product_name": data.get("product_name"),
                    "version": data.get("version"),
                    "claims": [],
                    "lineage": {"cites_prd": False, "cited_paths": [], "should_cite": []},
                    "drift": [],
                    "priority_fixes": ["tighten scope"],
                    "summary": "agent source",
                    "confidence": 0.9,
                }
            )
        return json.dumps(
            {
                "product_name": "Widget Pro",
                "canonical_prd": "PRD.md",
                "maturity": "draft",
                "completeness": {
                    "score": 42,
                    "must_present": ["problem"],
                    "must_missing": ["success"],
                    "should_missing": [],
                    "scattered": [],
                },
                "drift": [],
                "lineage": {"solid": [], "broken": [], "orphans": []},
                "prd_improvements": [],
                "alignment_actions": [],
                "open_questions": [],
                "context_brief": "agent brief",
                "confidence": 0.8,
            }
        )

    from app.services.prd_lineage.agent import PrdAgent

    cfg = PrdConfig(agent_enabled=True, agent_max_sources=4)
    agent = PrdAgent(cfg, runner=runner)
    inv = PrdLineageService(root=tmp_path / "ws", agent=agent).build(str(repo), cfg)
    assert inv.analysis_method == "agent"
    assert inv.analysis["context_brief"] == "agent brief"
    methods = {s.analysis_method for s in inv.sources if s.extracted}
    assert "agent" in methods


def test_parse_json_fences():
    assert parse_json('```json\n{"a": 1}\n```')["a"] == 1


def test_prompt_loader_has_prd_agents():
    loader = PromptLoader()
    analyst = loader.get_collection_item("agents", "prd-lineage-analyst")
    synth = loader.get_collection_item("agents", "prd-synthesizer")
    cmd = loader.get_collection_item("commands", "prd")
    assert analyst and "canonical_prd" in analyst["body"]
    assert synth and "alignment_actions" in synth["body"]
    assert cmd and cmd["name"] == "prd"


def test_exporters_unknown_format(tmp_path: Path):
    inv = PrdInventory(repo_root=str(tmp_path), repo_slug="x")
    try:
        exporters.render(inv, "pdf")
    except ValueError as exc:
        assert "Unknown format" in str(exc)
    else:
        raise AssertionError("expected ValueError")
