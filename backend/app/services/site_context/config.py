"""Tunable configuration for a site-context build.

One dataclass holds every knob for all three phases (map -> extract -> agent)
so callers can pass nothing and the surfaces (REST/MCP/CLI/script) can build one
from a loose JSON dict. Deliberately duck-type-compatible with
:class:`~app.services.site_snapshot.config.CrawlConfig` on the few attributes
the shared fetch/discovery helpers read (``use_cache``, ``refresh``,
``include_external``, ``denied_path_prefixes``).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, List, Optional

try:  # settings is available under the full and the CI dependency sets
    from ...core.config import settings

    _MAX_BYTES = int(settings.MAX_CONTENT_SIZE_BYTES)
except Exception:  # pragma: no cover - defensive, keep the package importable
    _MAX_BYTES = 10 * 1024 * 1024


# Unlike the snapshot crawler, a context build is *seeded on a section page*
# (e.g. /category/programming), so taxonomy prefixes must NOT be denied here —
# the seed itself would be excluded. Only true non-content paths are skipped.
DEFAULT_DENIED_PREFIXES: List[str] = ["/assets/", "/static/", "/cdn-cgi/"]

SCOPES = ("host", "domain", "path")
EXTRACTORS = ("auto", "builtin", "trafilatura")


@dataclass
class ContextConfig:
    """Knobs for a context build. All optional; defaults are polite and cheap."""

    # ---- phase 1: mapping ------------------------------------------------
    depth: int = 2  # levels BELOW the seed (0 = seed page only)
    scope: str = "host"  # host | domain (incl. subdomains) | path (under the seed)
    max_pages: int = 150
    max_pages_per_level: int = 80
    follow_sitemap: bool = False  # augment level 1 with in-scope sitemap URLs
    include_external: bool = False  # record off-scope refs always; crawl only if True
    skip_pagination: bool = True  # drop /page/2, ?page=3 style frontier traps
    denied_path_prefixes: List[str] = field(
        default_factory=lambda: list(DEFAULT_DENIED_PREFIXES)
    )

    # ---- rendering (optional; needs Playwright) --------------------------
    render: bool = False  # execute JavaScript and crawl the rendered DOM
    render_wait_ms: int = 600  # settle time after load before reading the DOM
    render_wait_until: str = "networkidle"

    # ---- fetching --------------------------------------------------------
    max_bytes_per_page: int = field(default_factory=lambda: _MAX_BYTES)
    delay_seconds: float = 0.25  # polite default; robots Crawl-delay can raise it
    timeout: float = 30.0
    respect_robots: bool = True
    use_cache: bool = True
    refresh: bool = False  # ignore validators, always re-fetch
    ttl_seconds: int = 0  # >0 skips revalidation for entries younger than this

    # ---- phase 2: extraction + metadata analysis -------------------------
    strip_boilerplate: bool = True  # extract main content (drop nav/footer chrome)
    keep_interactive: bool = True  # keep in-page tools (forms, demos) as content
    capture_presentation: bool = True  # styles / images / animation inventory
    fetch_stylesheets: bool = True  # fetch linked CSS (deduped) for real motion data
    max_stylesheets: int = 12
    max_stylesheet_bytes: int = 512 * 1024
    fetch_scripts: bool = True  # fetch same-host JS (deduped) for scripted motion
    max_scripts: int = 10
    max_script_bytes: int = 512 * 1024
    max_text_chars: int = 20000  # per-node stored plain text cap (0 = unlimited)
    # Main-content engine: auto (library for articles, built-in for hubs),
    # builtin, or trafilatura. Optional libraries are used only if installed.
    extractor: str = "auto"
    use_optional_libraries: bool = True  # trafilatura / extruct / protego when present

    # ---- phase 3: Claude Code agent (OAuth, no API key) ------------------
    agent_enabled: bool = True
    agent_model: Optional[str] = None  # default: claude_cli default ("sonnet")
    agent_max_pages: int = 25  # cap on per-page agent calls (cost guard)
    agent_concurrency: int = 3
    agent_timeout: int = 180  # seconds per call
    agent_synthesis: bool = True  # site-level synthesis pass after per-page loop
    agent_max_chars: int = 6000  # per-page text budget sent to the agent

    def __post_init__(self) -> None:
        if self.scope not in SCOPES:
            raise ValueError(f"scope must be one of {SCOPES}, got {self.scope!r}")
        if self.extractor not in EXTRACTORS:
            raise ValueError(
                f"extractor must be one of {EXTRACTORS}, got {self.extractor!r}"
            )
        self.depth = max(0, int(self.depth))

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "ContextConfig":
        """Build a config from a loose dict, ignoring unknown keys."""
        if not data:
            return cls()
        known = {f.name for f in fields(cls)}
        kwargs = {k: v for k, v in data.items() if k in known and v is not None}
        return cls(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
