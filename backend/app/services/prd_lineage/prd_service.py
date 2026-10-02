"""PrdLineageService — search a product repo, inventory PRD elements, align lineage."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import exporters
from .agent import PrdAgent
from .config import PrdConfig
from .extraction import extract_all
from .mapper import map_repo
from .model import PrdInventory, slugify

try:
    from ...core.config import workspace_root
except Exception:  # pragma: no cover

    def workspace_root() -> Path:
        return Path(".aieo-workspace").resolve()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PrdLineageService:
    def __init__(self, root: Optional[Path] = None, agent=None):
        self.root = Path(root) if root else None
        self._agent_override = agent

    def build(
        self,
        repo_root: str,
        cfg: Optional[PrdConfig] = None,
        *,
        map_only: bool = False,
    ) -> PrdInventory:
        cfg = cfg or PrdConfig()
        repo = Path(repo_root).expanduser().resolve()
        if not repo.is_dir():
            raise ValueError(f"Not a directory: {repo}")
        inv = PrdInventory(
            repo_root=str(repo),
            repo_slug=slugify(repo.name),
            created_at=_now_iso(),
            config=cfg.to_dict(),
        )
        start = time.monotonic()
        inv.sources = map_repo(repo, cfg)
        inv.phases["map"] = {
            "sources": len(inv.sources),
            "seconds": round(time.monotonic() - start, 2),
        }
        if map_only:
            inv.stats = {"sources_total": len(inv.sources)}
            inv.completed_at = _now_iso()
            return inv

        t2 = time.monotonic()
        inv.phases["extract"] = extract_all(inv, repo, cfg)
        inv.phases["extract"]["seconds"] = round(time.monotonic() - t2, 2)

        t3 = time.monotonic()
        agent = self._agent_override or PrdAgent(cfg)
        inv.phases["agent"] = agent.analyze(inv)
        inv.phases["agent"]["seconds"] = round(time.monotonic() - t3, 2)

        roles: Dict[str, int] = {}
        for src in inv.sources:
            roles[src.role] = roles.get(src.role, 0) + 1
        inv.stats = {
            "sources_total": len(inv.sources),
            "sources_extracted": sum(1 for s in inv.sources if s.extracted),
            "edges": len(inv.edges),
            "roles": roles,
            "elements_found": len(inv.element_index),
            "completeness": (inv.analysis or {}).get("completeness", {}).get("score"),
        }
        inv.completed_at = _now_iso()
        self._save(inv)
        return inv

    def run(
        self,
        repo_root: str,
        formats: Optional[List[str]] = None,
        cfg: Optional[PrdConfig] = None,
        *,
        map_only: bool = False,
        out_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        cfg = cfg or PrdConfig()
        inv = self.build(repo_root, cfg, map_only=map_only)
        formats = (
            formats
            or cfg.formats
            or (["json", "mermaid"] if map_only else ["json", "markdown"])
        )
        dest = Path(out_dir) if out_dir else self._out_dir(inv.repo_slug)
        outputs = exporters.write_outputs(inv, dest, formats)
        analysis = inv.analysis or {}
        return {
            "repo_root": inv.repo_root,
            "repo_slug": inv.repo_slug,
            "out_dir": str(dest),
            "stats": inv.stats,
            "phases": inv.phases,
            "degraded": inv.degraded,
            "analysis_method": inv.analysis_method,
            "product_name": analysis.get("product_name"),
            "canonical_prd": analysis.get("canonical_prd"),
            "maturity": analysis.get("maturity"),
            "context_brief": analysis.get("context_brief"),
            "completeness": (analysis.get("completeness") or {}).get("score"),
            "outputs": outputs,
            "manifest_path": str(self._manifest_path(inv.repo_slug)),
        }

    def load_manifest(self, repo_slug: str) -> Optional[Dict[str, Any]]:
        path = self._manifest_path(repo_slug)
        if not path.exists():
            return None
        import json

        return json.loads(path.read_text(encoding="utf-8"))

    def list_inventories(self) -> List[Dict[str, Any]]:
        cache = self._cache_dir()
        if not cache.exists():
            return []
        import json

        items = []
        for path in sorted(
            cache.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        ):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            items.append(
                {
                    "repo_slug": data.get("repo_slug") or path.stem,
                    "canonical_prd": (data.get("analysis") or {}).get("canonical_prd"),
                    "completeness": (data.get("stats") or {}).get("completeness"),
                    "completed_at": data.get("completed_at"),
                }
            )
        return items

    def _save(self, inv: PrdInventory) -> None:
        import json

        path = self._manifest_path(inv.repo_slug)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(inv.to_dict(), indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def _workspace(self) -> Path:
        return Path(self.root) if self.root else workspace_root()

    def _cache_dir(self) -> Path:
        return self._workspace() / ".cache" / "prd"

    def _manifest_path(self, slug: str) -> Path:
        return self._cache_dir() / f"{slug}.json"

    def _out_dir(self, slug: str) -> Path:
        return self._workspace() / "prd" / slug
