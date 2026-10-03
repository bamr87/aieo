"""Phase 3 — per-source and repo-level PRD analysis (Claude CLI or heuristic)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Sequence

from .config import PrdConfig
from .elements import COULD_IDS, MUST_IDS, SHOULD_IDS
from .model import PrdInventory, SourceNode

logger = logging.getLogger(__name__)

ANALYST_AGENT = "prd-lineage-analyst"
SYNTHESIZER_AGENT = "prd-synthesizer"
_MAX_CONSECUTIVE_FAILURES = 3

_PRIORITY_ROLES = (
    "canonical_prd",
    "readme",
    "changelog",
    "agent_instructions",
    "architecture",
    "api",
    "packaging",
)


class PrdAgent:
    def __init__(
        self,
        cfg: PrdConfig,
        *,
        prompt_loader=None,
        runner: Optional[Callable[..., str]] = None,
    ):
        self.cfg = cfg
        self._runner = runner
        self._prompt_loader = prompt_loader
        self._prompts: Dict[str, str] = {}
        self.unavailable_reason: Optional[str] = None
        self._consecutive_failures = 0
        self._tripped = False

    def available(self) -> bool:
        if not self.cfg.agent_enabled:
            self.unavailable_reason = "agent disabled by config"
            return False
        if self._runner is not None:
            return True
        try:
            from ..claude_cli import cli_available
        except Exception as exc:  # pragma: no cover
            self.unavailable_reason = f"claude_cli import failed: {exc}"
            return False
        if not cli_available():
            self.unavailable_reason = (
                "Claude Code CLI not found on PATH — analysis falls back to heuristics"
            )
            return False
        return True

    def analyze(self, inv: PrdInventory) -> Dict[str, Any]:
        targets = [s for s in inv.sources if s.extracted and not s.error]
        stats: Dict[str, Any] = {
            "candidates": len(targets),
            "agent_calls": 0,
            "agent_ok": 0,
            "agent_failed": 0,
            "heuristic": 0,
            "model": None,
            "provider": "claude-cli (OAuth)",
        }
        if not targets:
            stats["skipped_reason"] = "no extracted sources"
            inv.analysis = heuristic_synthesis(inv)
            inv.analysis_method = "heuristic"
            return stats

        use_agent = self.available()
        selected = self._select(targets) if use_agent else []
        for src in targets:
            if src in selected and use_agent and not self._tripped:
                ok = self._analyze_source(src, stats)
                if not ok:
                    self._apply_heuristic(src)
                    stats["heuristic"] += 1
            else:
                self._apply_heuristic(src)
                stats["heuristic"] += 1

        if self.cfg.agent_synthesis and use_agent and not self._tripped:
            synthesis = self._synthesize(inv, stats)
            if synthesis is not None:
                inv.analysis = synthesis
                inv.analysis_method = "agent"
                return stats

        inv.analysis = heuristic_synthesis(inv)
        inv.analysis_method = "heuristic"
        if use_agent:
            inv.degraded = True
        return stats

    def _select(self, targets: Sequence[SourceNode]) -> List[SourceNode]:
        ranked = sorted(
            targets,
            key=lambda s: (
                _PRIORITY_ROLES.index(s.role) if s.role in _PRIORITY_ROLES else 99,
                -s.word_count,
            ),
        )
        return list(ranked[: self.cfg.agent_max_sources])

    def _analyze_source(self, src: SourceNode, stats: Dict[str, Any]) -> bool:
        prompt = self._prompt(ANALYST_AGENT)
        payload = json.dumps(_source_payload(src), indent=2)
        stats["agent_calls"] += 1
        try:
            raw = self._call(prompt, payload)
            src.analysis = parse_json(raw)
            src.analysis_method = "agent"
            stats["agent_ok"] += 1
            self._consecutive_failures = 0
            return True
        except Exception as exc:
            src.analysis_error = str(exc)
            stats["agent_failed"] += 1
            self._consecutive_failures += 1
            if self._consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                self._tripped = True
            return False

    def _synthesize(
        self, inv: PrdInventory, stats: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        prompt = self._prompt(SYNTHESIZER_AGENT)
        payload = json.dumps(_inventory_payload(inv), indent=2)
        stats["agent_calls"] += 1
        try:
            raw = self._call(prompt, payload)
            parsed = parse_json(raw)
            stats["agent_ok"] += 1
            self._consecutive_failures = 0
            return parsed
        except Exception as exc:
            stats["agent_failed"] += 1
            stats["synthesis_error"] = str(exc)
            self._consecutive_failures += 1
            return None

    def _call(self, prompt: str, payload: str) -> str:
        if self._runner is not None:
            return self._runner(
                prompt=prompt, payload=payload, model=self.cfg.agent_model
            )
        from ..claude_cli import run_prompt

        return run_prompt(
            f"{prompt}\n\nInput:\n{payload}\n\nReturn JSON only.",
            model=self.cfg.agent_model,
            timeout=self.cfg.agent_timeout,
        )

    def _prompt(self, name: str) -> str:
        if name in self._prompts:
            return self._prompts[name]
        body = ""
        try:
            loader = self._prompt_loader
            if loader is None:
                from ..prompt_loader import PromptLoader

                loader = PromptLoader()
                self._prompt_loader = loader
            item = loader.get_collection_item("agents", name)
            if item:
                body = item.get("body") or ""
        except Exception as exc:  # pragma: no cover
            logger.debug("prompt load failed for %s: %s", name, exc)
        self._prompts[name] = (
            body or f"Analyze PRD lineage. Agent={name}. Return JSON only."
        )
        return self._prompts[name]

    def _apply_heuristic(self, src: SourceNode) -> None:
        src.analysis = heuristic_source(src)
        src.analysis_method = "heuristic"


def heuristic_source(src: SourceNode) -> Dict[str, Any]:
    cites_prd = any(Pathish(p).is_prd for p in src.outbound) or Pathish(src.path).is_prd
    return {
        "role": src.role,
        "is_product_spec": src.role == "canonical_prd",
        "elements_present": list(src.element_hits),
        "elements_missing_substance": [],
        "product_name": src.product_name,
        "version": src.version,
        "claims": src.headings[1:7],
        "lineage": {
            "cites_prd": cites_prd,
            "cited_paths": src.outbound[:12],
            "should_cite": [] if cites_prd or src.role == "canonical_prd" else ["PRD"],
        },
        "drift": [],
        "priority_fixes": [],
        "summary": (src.title or src.path)[:400],
        "confidence": 0.35,
        "_method": "heuristic",
    }


def heuristic_synthesis(inv: PrdInventory) -> Dict[str, Any]:
    present = {el for el, paths in inv.element_index.items() if paths}
    must_present = [e for e in MUST_IDS if e in present]
    must_missing = [e for e in MUST_IDS if e not in present]
    should_missing = [e for e in SHOULD_IDS if e not in present]
    could_present = [e for e in COULD_IDS if e in present]
    must_score = (len(must_present) / len(MUST_IDS)) * 70 if MUST_IDS else 0
    should_score = (
        ((len(SHOULD_IDS) - len(should_missing)) / len(SHOULD_IDS)) * 25
        if SHOULD_IDS
        else 0
    )
    could_score = (len(could_present) / len(COULD_IDS)) * 5 if COULD_IDS else 0
    score = round(must_score + should_score + could_score)
    canonical = inv.canonical
    names = _unique(s.product_name for s in inv.sources if s.product_name)
    versions = _unique(s.version for s in inv.sources if s.version)
    drift = []
    if len(names) > 1:
        drift.append(
            {
                "paths": [s.path for s in inv.sources if s.product_name],
                "field": "product_name",
                "values": names,
                "severity": "high",
            }
        )
    if len(versions) > 1:
        drift.append(
            {
                "paths": [s.path for s in inv.sources if s.version],
                "field": "version",
                "values": versions,
                "severity": "medium",
            }
        )
    prd_path = canonical.path if canonical else None
    cited = {e.source for e in inv.edges if prd_path and e.target == prd_path}
    witnesses = [
        s
        for s in inv.sources
        if s.role
        in ("readme", "changelog", "agent_instructions", "architecture", "api")
    ]
    broken = []
    solid = []
    if prd_path:
        for src in witnesses:
            if src.path in cited:
                solid.append({"from": src.path, "to": prd_path})
            else:
                broken.append(
                    {"from": src.path, "to": prd_path, "reason": "no citation"}
                )
    improvements = [
        {
            "element": el,
            "action": f"add {el} with measurable substance",
            "priority": "must",
        }
        for el in must_missing
    ]
    alignment = [
        {"path": b["from"], "action": f"cite {prd_path}", "priority": "must"}
        for b in broken
    ]
    if not canonical:
        improvements.insert(
            0,
            {
                "element": "executive_summary",
                "action": "create a canonical PRD covering must-elements",
                "priority": "must",
            },
        )
    maturity = _maturity(canonical, must_missing, score)
    product_name = names[0] if names else None
    brief = _brief(inv, product_name, canonical, score, must_missing)
    return {
        "product_name": product_name,
        "canonical_prd": prd_path,
        "maturity": maturity,
        "completeness": {
            "score": score,
            "must_present": must_present,
            "must_missing": must_missing,
            "should_missing": should_missing,
            "scattered": [
                {"element": el, "paths": paths}
                for el, paths in inv.element_index.items()
                if el in SHOULD_IDS + COULD_IDS
                and canonical
                and canonical.path not in paths
            ],
        },
        "drift": drift,
        "lineage": {"solid": solid, "broken": broken, "orphans": []},
        "prd_improvements": improvements,
        "alignment_actions": alignment,
        "open_questions": [],
        "context_brief": brief,
        "confidence": 0.4,
        "_method": "heuristic",
    }


def _maturity(canonical, must_missing, score: int) -> str:
    if canonical is None:
        return "none"
    if score < 30 or len(must_missing) >= 4:
        return "idea"
    if must_missing or score < 55:
        return "draft"
    if score < 80:
        return "mvp_ready"
    return "execution_ready"


def _brief(inv, product_name, canonical, score, must_missing) -> str:
    name = product_name or inv.repo_slug
    prd = canonical.path if canonical else "no canonical PRD"
    missing = ", ".join(must_missing[:5]) or "none"
    return (
        f"{name}: {len(inv.sources)} product-spec sources, canonical={prd}, "
        f"completeness={score}/100, must-missing={missing}."
    )


def _source_payload(src: SourceNode) -> Dict[str, Any]:
    return {
        "path": src.path,
        "role": src.role,
        "title": src.title,
        "headings": src.headings[:30],
        "element_hits": src.element_hits,
        "outbound": src.outbound[:20],
        "product_name": src.product_name,
        "version": src.version,
        "excerpt": src.excerpt[:4000],
    }


def _inventory_payload(inv: PrdInventory) -> Dict[str, Any]:
    return {
        "repo_slug": inv.repo_slug,
        "stats": inv.stats,
        "element_index": inv.element_index,
        "edges": [e.to_dict() for e in inv.edges[:80]],
        "sources": [
            {
                "path": s.path,
                "role": s.role,
                "product_name": s.product_name,
                "version": s.version,
                "element_hits": s.element_hits,
                "outbound": s.outbound[:12],
                "analysis": s.analysis or None,
            }
            for s in inv.sources
            if s.role in _PRIORITY_ROLES or s.role == "docs"
        ][:40],
    }


def parse_json(raw: str) -> Dict[str, Any]:
    cleaned = (raw or "").strip()
    if not cleaned:
        raise ValueError("agent returned empty output")
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            raise ValueError(f"agent returned non-JSON output: {cleaned[:200]}")
        parsed = json.loads(match.group())
    if not isinstance(parsed, dict):
        raise ValueError("agent returned JSON that is not an object")
    return parsed


def _unique(values) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values:
        key = value.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(value.strip())
    return out


class Pathish:
    def __init__(self, path: str):
        self.path = (path or "").replace("\\", "/").lower()

    @property
    def is_prd(self) -> bool:
        name = self.path.rsplit("/", 1)[-1]
        stem = name.rsplit(".", 1)[0]
        return stem == "prd" or stem.startswith("prd-")
