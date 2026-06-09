"""CLI: score and optionally optimize markdown files (DB-free, CI-friendly).

Run from repository root:
  pip install -r backend/requirements-ci.txt
  PYTHONPATH=backend python -m tools.aieo_runner --root /path/to/repo --mode audit-only
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Ensure backend package (app.*) is importable when run as __main__
_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# Load settings from environment only (avoid parsing repo .env complex fields)
os.environ.setdefault("AIEO_HEADLESS", "1")

from tools.aieo_runner.discover import (  # noqa: E402
    DEFAULT_IGNORE_DIR_NAMES,
    discover_files,
    discover_git_diff_paths,
    safe_relative,
)
from tools.aieo_runner.report import write_report_md  # noqa: E402

WORKFLOW_COMMANDS = {"research", "write", "rewrite", "analyze", "scrub", "priorities"}


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="AIEO headless markdown runner")
    p.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root containing markdown (default: cwd)",
    )
    p.add_argument(
        "--glob",
        dest="globs",
        action="append",
        default=[],
        metavar="PATTERN",
        help="Glob relative to root (repeatable). Default: **/*.md",
    )
    p.add_argument(
        "--git-diff-base",
        metavar="REF",
        default=None,
        help="Restrict to .md files changed between REF and HEAD (git three-dot)",
    )
    p.add_argument(
        "--intersect-globs",
        action="store_true",
        help="With --git-diff-base, only keep files that also match --glob patterns",
    )
    p.add_argument(
        "--ignore-dir",
        dest="ignore_dirs",
        action="append",
        default=[],
        metavar="NAME",
        help="Extra directory name to skip (repeatable)",
    )
    p.add_argument(
        "--mode",
        choices=("audit-only", "enhance", "expand"),
        default="audit-only",
        help="audit-only: score only; enhance/expand: score + AI rewrite",
    )
    p.add_argument(
        "--style",
        choices=("preserve", "aggressive"),
        default="preserve",
        help="Tone for enhance/expand",
    )
    p.add_argument(
        "--provider",
        choices=("openai", "anthropic"),
        default=None,
        help="AI provider (optional; inferred from API keys if omitted)",
    )
    p.add_argument("--model", default=None, help="Model name for optimize call")
    p.add_argument(
        "--api-key",
        default=None,
        help="API key (else OPENAI_API_KEY / ANTHROPIC_API_KEY env)",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("aieo-artifacts"),
        help="Directory for JSON, REPORT.md, proposed/",
    )
    p.add_argument(
        "--write-proposed",
        action="store_true",
        help="Write optimized markdown under output-dir/proposed/ (enhance/expand only)",
    )
    p.add_argument(
        "--apply-in-place",
        action="store_true",
        help="Overwrite source markdown with optimized content (enhance/expand only; use with care)",
    )
    p.add_argument(
        "--embed-proposed-in-json",
        action="store_true",
        help="Include optimized_content in per-file JSON (can be large)",
    )
    p.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="Process at most N files (0 = no limit)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write any files (stdout summary only)",
    )
    return p.parse_args()


def _parse_workflow_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="AIEO workflow commands")
    p.add_argument("command", choices=sorted(WORKFLOW_COMMANDS))
    p.add_argument("--workspace", type=Path, default=Path(".aieo-workspace"))
    p.add_argument("--topic", default="")
    p.add_argument("--source-path", default="")
    p.add_argument("--target", default="")
    p.add_argument("--content", default="")
    p.add_argument("--model", default=None)
    return p.parse_args(argv)


async def _run_workflow_command(args: argparse.Namespace) -> int:
    os.environ["WORKSPACE_ROOT"] = str(args.workspace)
    from app.services.research_service import ResearchService  # noqa: WPS433
    from app.services.write_service import WriteService  # noqa: WPS433
    from app.services.rewrite_service import RewriteService  # noqa: WPS433
    from app.services.analyze_existing_service import AnalyzeExistingService  # noqa: WPS433
    from app.services.scrub_service import ScrubService  # noqa: WPS433
    from app.services.priorities_service import PrioritiesService  # noqa: WPS433

    if args.command == "research":
        result = await ResearchService().create_brief(args.topic, model=args.model)
    elif args.command == "write":
        result = await WriteService().write(args.topic, model=args.model)
    elif args.command == "rewrite":
        result = await RewriteService().rewrite(args.source_path, model=args.model)
    elif args.command == "analyze":
        result = await AnalyzeExistingService().analyze(args.target, model=args.model)
    elif args.command == "scrub":
        result = await ScrubService().scrub(args.content, model=args.model)
    else:
        result = PrioritiesService().build_priorities()
    print(json.dumps(result, indent=2, default=str))
    return 0


def _collect_paths(args: argparse.Namespace) -> List[Path]:
    root = args.root.resolve()
    globs = args.globs if args.globs else ["**/*.md"]
    ignores: Set[str] = set(DEFAULT_IGNORE_DIR_NAMES) | set(args.ignore_dirs)

    glob_paths = {p.resolve() for p in discover_files(root, globs, ignores)}

    if args.git_diff_base:
        diff_paths = {p.resolve() for p in discover_git_diff_paths(root, args.git_diff_base)}
        if args.intersect_globs:
            paths = sorted(glob_paths & diff_paths, key=lambda x: str(x))
        else:
            paths = sorted(diff_paths, key=lambda x: str(x))
    else:
        paths = sorted(glob_paths, key=lambda x: str(x))

    if args.max_files and args.max_files > 0:
        paths = paths[: args.max_files]
    return paths


def _score_payload(score: Dict[str, Any], rel: str) -> Dict[str, Any]:
    return {
        "file": rel,
        "score": score.get("score"),
        "grade": score.get("grade"),
        "word_count": score.get("word_count"),
        "scoring_method": score.get("scoring_method"),
        "content_type": score.get("content_type"),
        "overall_assessment": score.get("overall_assessment"),
        "pattern_scores": score.get("pattern_scores"),
        "gaps": score.get("gaps"),
        "anti_pattern_penalties": score.get("anti_pattern_penalties"),
    }


async def _process_one(
    *,
    path: Path,
    root: Path,
    mode: str,
    style: str,
    opt,
    model: Optional[str],
) -> Dict[str, Any]:
    rel = safe_relative(path, root)
    text = path.read_text(encoding="utf-8")
    score = opt.scoring_engine.score(text, format="markdown")
    record: Dict[str, Any] = {
        "status": "success",
        "file": rel,
        **_score_payload(score, rel),
    }

    if mode == "audit-only":
        return record

    content_mode = "expand" if mode == "expand" else "enhance"
    ores = await opt.optimize(
        content=text,
        style=style,
        content_mode=content_mode,
        model=model,
    )
    record["score_before"] = ores.get("score_before")
    record["score_after"] = ores.get("score_after")
    record["uplift"] = ores.get("uplift")
    record["changes"] = ores.get("changes")
    record["optimized_content"] = ores.get("optimized_content")
    return record


async def _run_async(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    paths = _collect_paths(args)
    if not paths:
        print("No markdown files matched.", file=sys.stderr)
        return 1

    from app.services.optimize_service import OptimizeService  # noqa: WPS433

    opt = OptimizeService.for_provider(
        provider=args.provider,
        api_key=args.api_key,
        model=args.model,
    )

    if args.mode != "audit-only":
        if not (
            opt.ai_service.openai_client or opt.ai_service.anthropic_client
        ):
            print(
                "enhance/expand requires OPENAI_API_KEY or ANTHROPIC_API_KEY "
                "(or --api-key with --provider).",
                file=sys.stderr,
            )
            return 2

    out_dir = args.output_dir
    results_dir = out_dir / "results"
    proposed_dir = out_dir / "proposed"
    if not args.dry_run:
        results_dir.mkdir(parents=True, exist_ok=True)
        if args.write_proposed and args.mode != "audit-only":
            proposed_dir.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    for path in paths:
        rel = safe_relative(path, root)
        try:
            rec = await _process_one(
                path=path,
                root=root,
                mode=args.mode,
                style=args.style,
                opt=opt,
                model=args.model,
            )
        except Exception as e:  # noqa: BLE001
            rec = {
                "status": "error",
                "file": rel,
                "error": str(e),
            }
        rows.append(
            {
                "file": rel,
                "status": rec.get("status", "unknown"),
                "score": rec.get("score"),
                "grade": rec.get("grade"),
                "gap_count": len(rec.get("gaps") or []),
                "method": rec.get("scoring_method"),
                "error": rec.get("error"),
                "notes": "",
            }
        )

        if not args.dry_run:
            json_path = results_dir / f"{rel.replace('/', '__')}.json"
            json_path.parent.mkdir(parents=True, exist_ok=True)
            dump = {k: v for k, v in rec.items() if k != "optimized_content"}
            if args.embed_proposed_in_json and rec.get("optimized_content") is not None:
                dump["optimized_content"] = rec["optimized_content"]
            json_path.write_text(
                json.dumps(dump, indent=2, default=str),
                encoding="utf-8",
            )
            if (
                args.write_proposed
                and args.mode != "audit-only"
                and rec.get("status") == "success"
                and rec.get("optimized_content")
            ):
                prop_path = proposed_dir / rel
                prop_path.parent.mkdir(parents=True, exist_ok=True)
                prop_path.write_text(rec["optimized_content"], encoding="utf-8")

            if (
                args.apply_in_place
                and args.mode != "audit-only"
                and rec.get("status") == "success"
                and rec.get("optimized_content")
            ):
                path.write_text(rec["optimized_content"], encoding="utf-8")

        if rec.get("status") != "success":
            print(f"[{rec.get('status')}] {rel}: {rec.get('error', '')}", file=sys.stderr)

    if not args.dry_run:
        write_report_md(out_dir, rows)
        print(f"Wrote REPORT.md and results under {out_dir.resolve()}", file=sys.stderr)
    else:
        print(json.dumps(rows, indent=2, default=str))

    if any(r.get("status") == "error" for r in rows):
        return 1
    return 0


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in WORKFLOW_COMMANDS:
        wf_args = _parse_workflow_args(sys.argv[1:])
        raise SystemExit(asyncio.run(_run_workflow_command(wf_args)))
    args = _parse_args()
    raise SystemExit(asyncio.run(_run_async(args)))


if __name__ == "__main__":
    main()
