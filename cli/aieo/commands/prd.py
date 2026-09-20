"""`aieo prd` — inventory PRD elements in a product repo and align lineage."""

import json
import sys
from pathlib import Path

import click

_BACKEND = Path(__file__).resolve().parents[3] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


@click.command(name="prd")
@click.argument("repo_root", required=False, default=".")
@click.option("--formats", default="json,markdown", help="Comma list: json,markdown,mermaid")
@click.option("--output", "-o", type=click.Path(), help="Output directory")
@click.option("--max-files", default=400, show_default=True)
@click.option("--map-only", is_flag=True, help="Phase 1 only: classify sources")
@click.option("--no-agent", "no_agent", is_flag=True, help="Skip the Claude Code agent pass")
@click.option("--model", help="Claude Code model alias (default: sonnet)")
@click.option("--agent-sources", default=12, show_default=True, help="Max sources sent to the agent")
@click.option("--remote", is_flag=True, help="POST to the REST API instead of running in-process")
@click.option("--api-url", default="http://localhost:8000/api/v1", help="API base URL (with --remote)")
@click.option("--api-key", envvar="AIEO_API_KEY", help="API key (or set AIEO_API_KEY)")
@click.option("--json", "output_json", is_flag=True, help="Print the raw result JSON")
def prd(
    repo_root,
    formats,
    output,
    max_files,
    map_only,
    no_agent,
    model,
    agent_sources,
    remote,
    api_url,
    api_key,
    output_json,
):
    """Search REPO_ROOT for PRD elements and lineage witnesses, then align them.

    Three phases: map product-spec sources, extract element hits and citations,
    then analyze completeness/drift (Claude Code over OAuth, heuristic fallback).
    """
    fmt_list = [f.strip() for f in formats.split(",") if f.strip()]
    knobs = {
        "max_files": max_files,
        "agent_enabled": not no_agent,
        "agent_model": model,
        "agent_max_sources": agent_sources,
    }
    if remote:
        result = _run_remote(repo_root, fmt_list, knobs, map_only, api_url, api_key)
    else:
        result = _run_local(repo_root, fmt_list, knobs, map_only, output)

    if output_json:
        click.echo(json.dumps(result, indent=2, default=str))
        return

    stats = result.get("stats") or {}
    phases = result.get("phases") or {}
    click.echo(f"\nRepo:     {result.get('repo_root', repo_root)}")
    click.echo(f"Product:  {result.get('product_name') or 'unknown'}")
    click.echo(f"PRD:      {result.get('canonical_prd') or 'missing'}")
    click.echo(
        f"Map:      {stats.get('sources_total', 0)} sources, "
        f"{stats.get('edges', 0)} citations"
    )
    extract = phases.get("extract") or {}
    if "skipped" in extract:
        click.echo(f"Extract:  skipped ({extract['skipped']})")
    elif extract:
        click.echo(f"Extract:  {extract.get('extracted', 0)} files")
    agent = phases.get("agent") or {}
    if map_only:
        click.echo("Agent:    skipped (map-only)")
    elif "skipped_reason" in agent:
        click.echo(f"Agent:    skipped ({agent['skipped_reason']})")
    else:
        click.echo(
            f"Agent:    {agent.get('agent_ok', 0)}/{agent.get('agent_calls', 0)} calls, "
            f"{agent.get('heuristic', 0)} heuristic [{result.get('analysis_method')}]"
        )
    if result.get("completeness") is not None:
        click.echo(
            f"Score:    {result.get('completeness')}/100  maturity={result.get('maturity')}"
        )
    if result.get("context_brief"):
        click.echo(f"Brief:    {result['context_brief'][:280]}")
    click.echo(f"Output:   {result.get('out_dir', '(remote)')}")
    for fmt, info in (result.get("outputs") or {}).items():
        if "error" in info:
            click.echo(f"  - {fmt}: ERROR {info['error']}")
        else:
            click.echo(f"  - {fmt}: {info.get('bytes', 0):,} bytes {info.get('path', '')}")


def _run_local(repo_root, formats, knobs, map_only, output):
    from app.services.prd_lineage import PrdConfig, PrdLineageService

    cfg = PrdConfig.from_dict(knobs)
    svc = PrdLineageService()
    out_dir = Path(output) if output else None
    return svc.run(repo_root, formats=formats, cfg=cfg, map_only=map_only, out_dir=out_dir)


def _run_remote(repo_root, formats, knobs, map_only, api_url, api_key):
    import httpx

    payload = {"repo_root": str(Path(repo_root).resolve()), "formats": formats, "map_only": map_only}
    payload.update(knobs)
    headers = {"X-API-Key": api_key} if api_key else {}
    with httpx.Client(timeout=300) as client:
        resp = client.post(f"{api_url}/aieo/prd", json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()
