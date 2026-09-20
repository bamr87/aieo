"""Exporters for a PRD-lineage inventory."""

from __future__ import annotations

import io
import json
from typing import Any, Dict

from .elements import ELEMENTS
from .model import PrdInventory

FORMATS = ["json", "markdown", "mermaid"]
_EXT = {"json": ".json", "markdown": ".md", "mermaid": ".mmd"}


def extension_for(fmt: str) -> str:
    return _EXT.get(fmt, ".txt")


def render(inv: PrdInventory, fmt: str) -> str:
    if fmt == "json":
        return export_json(inv)
    if fmt == "markdown":
        return export_markdown(inv)
    if fmt == "mermaid":
        return export_mermaid(inv)
    raise ValueError(f"Unknown format: {fmt}")


def export_json(inv: PrdInventory) -> str:
    return json.dumps(inv.to_dict(), indent=2, ensure_ascii=False, default=str)


def export_markdown(inv: PrdInventory) -> str:
    out = io.StringIO()
    w = out.write
    analysis = inv.analysis or {}
    completeness = analysis.get("completeness") or {}
    w(f"# PRD lineage: {inv.repo_slug}\n\n")
    w(f"- **Repo**: `{inv.repo_root}`\n")
    w(f"- **Product**: {analysis.get('product_name') or 'unknown'}\n")
    w(f"- **Canonical PRD**: {analysis.get('canonical_prd') or 'missing'}\n")
    w(f"- **Maturity**: {analysis.get('maturity') or 'unknown'}\n")
    w(f"- **Completeness**: {completeness.get('score', 0)}/100\n")
    w(f"- **Analysis**: {inv.analysis_method}\n")
    w(f"- **Sources**: {len(inv.sources)}\n\n")
    if analysis.get("context_brief"):
        w(f"{analysis['context_brief']}\n\n")

    w("## Element coverage\n\n")
    w("| Element | Required | Sources |\n|---|---|---|\n")
    for el in ELEMENTS:
        paths = inv.element_index.get(el.id) or []
        loc = ", ".join(f"`{p}`" for p in paths[:4]) or "—"
        w(f"| {el.name} (`{el.id}`) | {el.required} | {loc} |\n")
    w("\n")

    missing = completeness.get("must_missing") or []
    if missing:
        w("## Missing must-elements\n\n")
        for el in missing:
            w(f"- `{el}`\n")
        w("\n")

    drift = analysis.get("drift") or []
    if drift:
        w("## Drift\n\n")
        for item in drift:
            w(
                f"- **{item.get('field')}** {item.get('values')} "
                f"({item.get('severity')}) in {item.get('paths')}\n"
            )
        w("\n")

    w("## Lineage actions\n\n")
    for action in analysis.get("alignment_actions") or []:
        w(f"- `{action.get('path')}`: {action.get('action')} [{action.get('priority')}]\n")
    for action in analysis.get("prd_improvements") or []:
        w(
            f"- PRD `{action.get('element')}`: {action.get('action')} "
            f"[{action.get('priority')}]\n"
        )
    if not (analysis.get("alignment_actions") or analysis.get("prd_improvements")):
        w("- none\n")
    w("\n")

    w("## Sources\n\n")
    w("| Path | Role | Elements | Version |\n|---|---|---|---|\n")
    for src in inv.sources:
        hits = ", ".join(src.element_hits[:6]) or "—"
        w(f"| `{src.path}` | {src.role} | {hits} | {src.version or '—'} |\n")
    return out.getvalue()


def export_mermaid(inv: PrdInventory) -> str:
    lines = ["flowchart LR"]
    seen = set()

    def nid(path: str) -> str:
        return "n" + str(abs(hash(path)) % 10_000_000)

    for src in inv.sources:
        if src.role in ("prompt_spec", "other") and src.path not in {
            e.source for e in inv.edges
        } | {e.target for e in inv.edges}:
            continue
        ident = nid(src.path)
        if ident in seen:
            continue
        seen.add(ident)
        label = f"{src.path}\\n{src.role}"
        shape = f'["{label}"]' if src.role != "canonical_prd" else f'(["{label}"])'
        lines.append(f"  {ident}{shape}")
    for edge in inv.edges:
        lines.append(f"  {nid(edge.source)} --> {nid(edge.target)}")
    return "\n".join(lines) + "\n"


def write_outputs(inv: PrdInventory, out_dir, formats) -> Dict[str, Any]:
    from pathlib import Path

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs: Dict[str, Any] = {}
    for fmt in formats:
        try:
            text = render(inv, fmt)
            path = out_dir / f"{inv.repo_slug}{extension_for(fmt)}"
            path.write_text(text, encoding="utf-8")
            outputs[fmt] = {"path": str(path), "bytes": path.stat().st_size}
        except Exception as exc:
            outputs[fmt] = {"error": str(exc)}
    return outputs
