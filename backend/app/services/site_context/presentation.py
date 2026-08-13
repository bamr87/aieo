"""Phase 2a — what a page *looks like*: styles, imagery and motion.

The content extractor answers "what does this page say"; this module answers
"how is it presented". It reads three surfaces and merges them:

* the **HTML** — ``<img>``/``<picture>``/``<svg>``/``<video>``/``<canvas>``,
  inline ``<style>`` blocks, ``style=`` attributes, script and stylesheet refs;
* the **linked CSS** — fetched once per site and shared across pages (a theme's
  stylesheet is the same file on every page), which is where nearly all real
  animation lives: ``@keyframes``, ``animation``/``transition`` declarations,
  ``prefers-reduced-motion`` guards, the colour palette and the type stack;
* the **linked JavaScript** — same-host scripts, fetched once per site like
  the CSS. Without it a page whose entire point is a ``requestAnimationFrame``
  canvas or SVG animation profiles as "static", because nothing in its markup
  or CSS moves;
* **library fingerprints** — GSAP, Lottie, AOS, Framer Motion, Three.js,
  Tailwind, Bootstrap, React/Vue/Svelte and friends, matched against script
  sources, stylesheet hrefs, inline script text and CSS custom-property
  prefixes.

It also inventories a page's **interactive UI** — controls, their labels, and
the demo containers that hold them. Prose extractors throw this away; on a page
whose payload is a live tool ("Live demo (JavaScript)"), throwing it away leaves
a section heading with nothing under it.

Everything here is deterministic and offline: it emits *facts* (counts, names,
coverage ratios), never judgements — judgement is the agent's job.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Tuple
from urllib.parse import urljoin

# --------------------------------------------------------------------------- #
# Fingerprints (matched against script src / link href / inline script / CSS)
# --------------------------------------------------------------------------- #
_ANIMATION_LIBS: Tuple[Tuple[str, str], ...] = (
    ("gsap", r"\bgsap\b|greensock|TweenMax|ScrollTrigger"),
    ("framer-motion", r"framer-motion|framerusercontent"),
    ("anime.js", r"\banime(?:\.min)?\.js\b|animejs"),
    ("lottie", r"lottie"),
    ("three.js", r"\bthree(?:\.min)?\.js\b|THREE\."),
    ("aos", r"\baos(?:\.min)?\.(?:js|css)\b|data-aos"),
    ("scrollreveal", r"scrollreveal|ScrollReveal\("),
    ("animate.css", r"animate\.(?:min\.)?css|\banimate__animated\b"),
    ("wow.js", r"\bwow(?:\.min)?\.js\b|\bwow\s+fadeIn"),
    ("velocity", r"velocity(?:\.min)?\.js"),
    ("motion-one", r"\bmotion(?:\.min)?\.js\b|@motionone"),
    ("swiper", r"swiper(?:-bundle)?(?:\.min)?\.(?:js|css)"),
    ("splide", r"splide(?:\.min)?\.(?:js|css)"),
    ("particles", r"particles\.js|tsparticles"),
    ("locomotive-scroll", r"locomotive-scroll"),
    ("rellax", r"rellax(?:\.min)?\.js"),
    ("barba", r"barba(?:\.min)?\.js"),
    ("typed.js", r"typed(?:\.min)?\.js"),
    ("lax.js", r"\blax(?:\.min)?\.js\b"),
)

_CSS_FRAMEWORKS: Tuple[Tuple[str, str], ...] = (
    ("tailwind", r"tailwind|--tw-[\w-]+"),
    ("bootstrap", r"bootstrap(?:\.min)?\.(?:css|js)|--bs-[\w-]+"),
    ("bulma", r"bulma(?:\.min)?\.css"),
    ("foundation", r"foundation(?:\.min)?\.css"),
    ("materialize", r"materialize(?:\.min)?\.css|material-components"),
    ("semantic-ui", r"semantic(?:\.min)?\.css"),
    ("pico.css", r"\bpico(?:\.min)?\.css"),
    ("water.css", r"water(?:\.min)?\.css"),
    ("normalize.css", r"normalize(?:\.min)?\.css"),
    ("font-awesome", r"font-?awesome"),
    ("minima", r"minima"),  # the default Jekyll theme
)

_JS_FRAMEWORKS: Tuple[Tuple[str, str], ...] = (
    ("next.js", r"/_next/|__NEXT_DATA__"),
    ("nuxt", r"__NUXT__|/_nuxt/"),
    (
        "react",
        r"data-reactroot|react(?:-dom)?(?:\.production)?(?:\.min)?\.js|__reactContainer",
    ),
    ("vue", r"\bvue(?:\.runtime)?(?:\.min)?\.js\b|data-v-[0-9a-f]{6,}"),
    ("svelte", r"\bsvelte(?:kit)?\b|svelte-[0-9a-z]{5,}"),
    ("angular", r"ng-version|angular(?:\.min)?\.js"),
    ("astro", r"astro-island|astro/"),
    ("gatsby", r"___gatsby|gatsby-"),
    ("jquery", r"jquery(?:[-.]\d|(?:\.min)?\.js)"),
    ("htmx", r"\bhtmx(?:\.min)?\.js\b|hx-get="),
    ("alpine.js", r"alpinejs|\bx-data\b"),
    ("stimulus", r"stimulus(?:\.min)?\.js|data-controller="),
)

# --------------------------------------------------------------------------- #
# CSS regexes
# --------------------------------------------------------------------------- #
_KEYFRAMES_RE = re.compile(r"@(?:-webkit-|-moz-|-o-)?keyframes\s+([\w-]+)", re.I)
_ANIMATION_DECL_RE = re.compile(r"(?<![\w-])animation(?:-name|-duration)?\s*:", re.I)
_TRANSITION_DECL_RE = re.compile(
    r"(?<![\w-])transition(?:-property|-duration)?\s*:", re.I
)
_TRANSFORM_DECL_RE = re.compile(r"(?<![\w-])transform\s*:", re.I)
_WILL_CHANGE_RE = re.compile(r"(?<![\w-])will-change\s*:", re.I)
_REDUCED_MOTION_RE = re.compile(r"prefers-reduced-motion", re.I)
_SMOOTH_SCROLL_RE = re.compile(r"scroll-behavior\s*:\s*smooth", re.I)
_MEDIA_RE = re.compile(r"@media[^{]{0,200}", re.I)
_BREAKPOINT_RE = re.compile(
    r"\((?:min|max)-width\s*:\s*(\d+(?:\.\d+)?)(px|r?em)\)", re.I
)
_CUSTOM_PROP_RE = re.compile(r"(--[\w-]+)\s*:\s*([^;{}]{1,120})")
_FONT_FAMILY_RE = re.compile(r"font-family\s*:\s*([^;{}]{1,200})", re.I)
_FONT_FACE_RE = re.compile(r"@font-face", re.I)
_HEX_RE = re.compile(r"#([0-9a-f]{3}|[0-9a-f]{4}|[0-9a-f]{6}|[0-9a-f]{8})\b", re.I)
_FUNC_COLOR_RE = re.compile(r"\b(?:rgba?|hsla?|oklch|lab)\([^)]{1,80}\)", re.I)
_BG_IMAGE_RE = re.compile(
    r"background(?:-image)?\s*:[^;{}]*url\(\s*['\"]?([^'\")]+)", re.I
)
_GRID_RE = re.compile(r"display\s*:\s*(?:inline-)?grid", re.I)
_FLEX_RE = re.compile(r"display\s*:\s*(?:inline-)?flex", re.I)
_DARK_RE = re.compile(r"prefers-color-scheme\s*:\s*dark", re.I)
_CONTAINER_QUERY_RE = re.compile(r"@container", re.I)

_RAF_RE = re.compile(r"requestAnimationFrame", re.I)
_TIMER_ANIM_RE = re.compile(r"set(?:Interval|Timeout)\s*\(", re.I)
_CANVAS_CTX_RE = re.compile(r"getContext\s*\(\s*['\"](2d|webgl2?|bitmaprenderer)", re.I)
# Real scripts rarely spell the SVG namespace out — nayuki's uses
# `createElementNS(svg.namespaceURI, tag)` — so match the call, not the literal.
_SVG_BUILD_RE = re.compile(r"createElementNS\s*\(", re.I)
_STYLE_MUTATE_RE = re.compile(
    r"\.style\.(?:transform|opacity|left|top|width|height)\s*=|"
    r"setAttribute\s*\(\s*['\"](?:transform|cx|cy|x1|y1|d|points|opacity)['\"]",
    re.I,
)
_LISTENER_RE = re.compile(r"addEventListener\s*\(\s*['\"]([a-z]+)['\"]", re.I)
_REVEAL_RE = re.compile(
    r"\.hidden\s*=\s*(?:false|!1)|removeAttribute\s*\(\s*['\"]hidden", re.I
)
_WAAPI_RE = re.compile(r"\.animate\s*\(", re.I)
_INTERSECTION_RE = re.compile(r"IntersectionObserver", re.I)
_SCROLL_LISTENER_RE = re.compile(r"addEventListener\(\s*['\"]scroll['\"]", re.I)

_IMG_EXT_RE = re.compile(
    r"\.(avif|webp|svg|png|jpe?g|gif|bmp|ico|tiff?)(?:$|[?#])", re.I
)
_MAX_ITEMS = 40


def stylesheet_urls(html: str, page_url: str, limit: int = 20) -> List[str]:
    """Absolute URLs of the page's linked stylesheets (order preserved)."""
    soup = _soup(html)
    if soup is None:
        return []
    out: List[str] = []
    for link in soup.find_all("link", href=True):
        rels = [r.lower() for r in (link.get("rel") or [])]
        if "stylesheet" not in rels:
            continue
        absolute = urljoin(page_url, link["href"])
        if absolute.lower().startswith(("http://", "https://")) and absolute not in out:
            out.append(absolute)
        if len(out) >= limit:
            break
    return out


def script_urls(html: str, page_url: str, limit: int = 12) -> List[str]:
    """Absolute URLs of the page's external scripts (order preserved)."""
    soup = _soup(html)
    if soup is None:
        return []
    out: List[str] = []
    for tag in soup.find_all("script", src=True):
        absolute = urljoin(page_url, tag["src"])
        if absolute.lower().startswith(("http://", "https://")) and absolute not in out:
            out.append(absolute)
        if len(out) >= limit:
            break
    return out


def analyze(
    html: str, page_url: str, css_text: str = "", js_text: str = ""
) -> Dict[str, Any]:
    """Full presentation profile for one page.

    ``css_text`` / ``js_text`` are the (already fetched, already deduped)
    concatenations of the page's linked stylesheets and same-host scripts.
    """
    soup = _soup(html)
    if soup is None:  # pragma: no cover - bs4 is in the lean dependency set
        return {}

    inline_styles = [s.get_text() or "" for s in soup.find_all("style")]
    inline_css = "\n".join(inline_styles)
    all_css = f"{css_text}\n{inline_css}" if css_text else inline_css

    scripts_ext = [
        urljoin(page_url, s["src"]) for s in soup.find_all("script", src=True)
    ]
    inline_scripts = [
        s.get_text() or "" for s in soup.find_all("script") if not s.get("src")
    ]
    inline_js = "\n".join(inline_scripts)
    all_js = f"{inline_js}\n{js_text}" if js_text else inline_js
    link_hrefs = [
        urljoin(page_url, ln["href"]) for ln in soup.find_all("link", href=True)
    ]

    # One haystack for every fingerprint family.
    haystack = "\n".join(
        [
            " ".join(scripts_ext),
            " ".join(link_hrefs),
            all_js[:400_000],
            all_css[:400_000],
            _class_sample(soup),
        ]
    )

    return {
        "styles": _styles(soup, all_css, inline_styles, link_hrefs, haystack, page_url),
        "images": _images(soup, page_url, all_css),
        "animation": _animation(soup, all_css, all_js, haystack),
        "interactivity": _interactivity(soup, all_js),
        "scripts": _scripts(soup, scripts_ext, inline_scripts, haystack, js_text),
    }


# --------------------------------------------------------------------------- #
# Styles
# --------------------------------------------------------------------------- #
def _styles(soup, css, inline_styles, link_hrefs, haystack, page_url) -> Dict[str, Any]:
    breakpoints = sorted(
        {
            f"{int(float(value))}{unit.lower()}"
            for value, unit in _BREAKPOINT_RE.findall(css)
        },
        key=lambda b: float(re.sub(r"[a-z]+$", "", b)),
    )
    theme_color = soup.find("meta", attrs={"name": re.compile(r"^theme-color$", re.I)})
    return {
        "stylesheets": [
            h for h in link_hrefs if h.lower().split("?")[0].endswith(".css")
        ][:20],
        "stylesheet_count": len(
            [
                ln
                for ln in soup.find_all("link", href=True)
                if "stylesheet" in [r.lower() for r in (ln.get("rel") or [])]
            ]
        ),
        "inline_style_blocks": len(inline_styles),
        "inline_style_bytes": sum(len(s) for s in inline_styles),
        "inline_style_attrs": len(soup.select("[style]")),
        "css_bytes_analyzed": len(css),
        "frameworks": _match_libs(_CSS_FRAMEWORKS, haystack),
        "palette": _palette(css),
        "custom_properties": _custom_properties(css),
        "font_families": _fonts(css, soup),
        "font_face_rules": len(_FONT_FACE_RE.findall(css)),
        "google_fonts": [h for h in link_hrefs if "fonts.g" in h.lower()][:5],
        "media_queries": len(_MEDIA_RE.findall(css)),
        "breakpoints": breakpoints[:12],
        "container_queries": len(_CONTAINER_QUERY_RE.findall(css)),
        "uses_flexbox": bool(_FLEX_RE.search(css)),
        "uses_grid": bool(_GRID_RE.search(css)),
        "dark_mode": bool(_DARK_RE.search(css)),
        "theme_color": theme_color.get("content") if theme_color else None,
        "responsive_meta": bool(
            soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
        ),
    }


def _palette(css: str) -> List[Dict[str, Any]]:
    counter: Counter = Counter()
    for match in _HEX_RE.findall(css):
        counter[_expand_hex(match)] += 1
    for match in _FUNC_COLOR_RE.findall(css):
        counter[re.sub(r"\s+", "", match.lower())] += 1
    return [{"color": c, "count": n} for c, n in counter.most_common(12)]


def _expand_hex(digits: str) -> str:
    digits = digits.lower()
    if len(digits) in (3, 4):
        digits = "".join(ch * 2 for ch in digits)
    return f"#{digits}"


def _custom_properties(css: str) -> Dict[str, str]:
    props: Dict[str, str] = {}
    for name, value in _CUSTOM_PROP_RE.findall(css):
        props.setdefault(name, value.strip())
        if len(props) >= 40:
            break
    return props


def _fonts(css: str, soup) -> List[str]:
    counter: Counter = Counter()
    for stack in _FONT_FAMILY_RE.findall(css):
        first = stack.split(",")[0].strip().strip("'\"")
        if first and not first.startswith("var(") and len(first) < 60:
            counter[first] += 1
    for el in soup.select("[style*='font-family']")[:50]:
        match = _FONT_FAMILY_RE.search(el.get("style", ""))
        if match:
            counter[match.group(1).split(",")[0].strip().strip("'\"")] += 1
    return [name for name, _ in counter.most_common(8)]


# --------------------------------------------------------------------------- #
# Images
# --------------------------------------------------------------------------- #
def _images(soup, page_url: str, css: str) -> Dict[str, Any]:
    imgs = soup.find_all("img")
    items: List[Dict[str, Any]] = []
    formats: Counter = Counter()
    with_alt = lazy = dimensioned = responsive = decorative = 0

    for img in imgs:
        src = img.get("src") or img.get("data-src") or ""
        absolute = urljoin(page_url, src) if src else ""
        alt = img.get("alt")
        has_dims = bool(img.get("width") and img.get("height"))
        srcset = bool(img.get("srcset") or img.get("data-srcset"))
        loading = (img.get("loading") or "").lower()
        fmt = _image_format(absolute)
        formats[fmt] += 1
        if alt is not None and alt.strip():
            with_alt += 1
        elif alt is not None:
            decorative += 1  # alt="" is a valid decorative marker, not a defect
        if loading == "lazy":
            lazy += 1
        if has_dims:
            dimensioned += 1
        if srcset:
            responsive += 1
        if len(items) < _MAX_ITEMS:
            items.append(
                {
                    "src": absolute,
                    "alt": alt,
                    "format": fmt,
                    "width": img.get("width"),
                    "height": img.get("height"),
                    "loading": loading or None,
                    "responsive": srcset,
                    "title": img.get("title"),
                }
            )

    total = len(imgs)
    backgrounds = [m for m in _BG_IMAGE_RE.findall(css) if not m.startswith("data:")]
    picture_sources = soup.find_all("source")
    icons = [
        urljoin(page_url, ln["href"])
        for ln in soup.find_all("link", href=True)
        if any("icon" in r.lower() for r in (ln.get("rel") or []))
    ]
    og_image = soup.find("meta", attrs={"property": "og:image"})

    return {
        "count": total,
        "items": items,
        "formats": dict(formats.most_common()),
        "with_alt": with_alt,
        "decorative_alt": decorative,
        "missing_alt": max(total - with_alt - decorative, 0),
        "alt_coverage": round((with_alt + decorative) / total, 3) if total else None,
        "lazy_loaded": lazy,
        "with_dimensions": dimensioned,
        "responsive_srcset": responsive,
        "picture_sources": len(picture_sources),
        "inline_svg": len(soup.find_all("svg")),
        "css_background_images": len(backgrounds),
        "background_samples": [_short(u) for u in dict.fromkeys(backgrounds)][:10],
        "icons": icons[:5],
        "og_image": og_image.get("content") if og_image else None,
    }


def _image_format(url: str) -> str:
    match = _IMG_EXT_RE.search(url or "")
    if not match:
        return "unknown"
    ext = match.group(1).lower()
    return "jpeg" if ext in ("jpg", "jpeg") else ext


# --------------------------------------------------------------------------- #
# Animation / motion
# --------------------------------------------------------------------------- #
def _animation(soup, css: str, js: str, haystack: str) -> Dict[str, Any]:
    keyframes = list(dict.fromkeys(_KEYFRAMES_RE.findall(css)))[:30]
    videos = soup.find_all("video")
    svg_smil = len(
        soup.find_all(["animate", "animateTransform", "animateMotion", "set"])
    )
    libs = _match_libs(_ANIMATION_LIBS, haystack)

    profile = {
        "keyframes": keyframes,
        "keyframe_count": len(keyframes),
        "animation_declarations": len(_ANIMATION_DECL_RE.findall(css)),
        "transition_declarations": len(_TRANSITION_DECL_RE.findall(css)),
        "transform_declarations": len(_TRANSFORM_DECL_RE.findall(css)),
        "will_change": len(_WILL_CHANGE_RE.findall(css)),
        "smooth_scroll": bool(_SMOOTH_SCROLL_RE.search(css)),
        "respects_reduced_motion": bool(_REDUCED_MOTION_RE.search(css)),
        "libraries": libs,
        "svg_smil_elements": svg_smil,
        "canvas_elements": len(soup.find_all("canvas")),
        "video": {
            "count": len(videos),
            "autoplay": sum(1 for v in videos if v.has_attr("autoplay")),
            "loop": sum(1 for v in videos if v.has_attr("loop")),
            "muted": sum(1 for v in videos if v.has_attr("muted")),
        },
        "animated_gifs": sum(
            1
            for img in soup.find_all("img")
            if (img.get("src") or "").lower().split("?")[0].endswith(".gif")
        ),
        "web_animations_api": bool(_WAAPI_RE.search(js)),
        "request_animation_frame": bool(_RAF_RE.search(js)),
        "canvas_drawing": bool(_CANVAS_CTX_RE.search(js)),
        "svg_scripted": bool(_SVG_BUILD_RE.search(js)),
        "timer_driven": bool(_TIMER_ANIM_RE.search(js)),
        "style_mutation": bool(_STYLE_MUTATE_RE.search(js)),
        "intersection_observer": bool(_INTERSECTION_RE.search(js)),
        "scroll_listeners": len(_SCROLL_LISTENER_RE.findall(js)),
        "lottie_players": len(soup.find_all(re.compile(r"lottie", re.I))),
    }
    profile["has_motion"] = bool(
        profile["keyframe_count"]
        or profile["animation_declarations"]
        or profile["transition_declarations"]
        or libs
        or profile["video"]["count"]
        or svg_smil
        or profile["canvas_elements"]
        or profile["web_animations_api"]
        # Script-driven motion: the page's own JS drives the animation, so no
        # amount of CSS or markup inspection would ever see it. A bare timer is
        # too weak on its own (polling looks the same), so it only counts when
        # the script is also building or mutating what is on screen.
        or profile["request_animation_frame"]
        or profile["canvas_drawing"]
        or profile["svg_scripted"]
        or (profile["timer_driven"] and profile["style_mutation"])
    )
    profile["signals"] = _motion_signals(profile)
    return profile


def _motion_signals(p: Dict[str, Any]) -> List[str]:
    """Short human/agent-readable notes about how the page moves."""
    out: List[str] = []
    if p["keyframe_count"]:
        out.append(
            f"{p['keyframe_count']} CSS @keyframes ({', '.join(p['keyframes'][:5])})"
        )
    if p["transition_declarations"]:
        out.append(f"{p['transition_declarations']} CSS transition declarations")
    if p["libraries"]:
        out.append("animation libraries: " + ", ".join(p["libraries"]))
    if p["video"]["autoplay"]:
        out.append(f"{p['video']['autoplay']} autoplaying video(s)")
    if p["canvas_elements"]:
        out.append(f"{p['canvas_elements']} <canvas> element(s)")
    if p["svg_smil_elements"]:
        out.append(f"{p['svg_smil_elements']} SVG SMIL animation element(s)")
    if p["scroll_listeners"] or p["intersection_observer"]:
        out.append("scroll-driven effects")
    script_driven = [
        name
        for name, on in (
            ("requestAnimationFrame loop", p["request_animation_frame"]),
            ("scripted canvas drawing", p["canvas_drawing"]),
            ("scripted SVG construction", p["svg_scripted"]),
            ("Web Animations API", p["web_animations_api"]),
            ("timer-driven redraw", p["timer_driven"] and p["style_mutation"]),
        )
        if on
    ]
    if script_driven:
        out.append("script-driven motion: " + ", ".join(script_driven))
    if p["has_motion"] and not p["respects_reduced_motion"]:
        out.append("no prefers-reduced-motion guard")
    if not p["has_motion"]:
        out.append("static: no motion detected")
    return out


# --------------------------------------------------------------------------- #
# Interactivity (in-page tools: demos, calculators, generators)
# --------------------------------------------------------------------------- #
_DEMO_HEADING_RE = re.compile(
    r"\b(demo|interactive|try it|playground|calculator|generator|simulator|"
    r"visuali[sz]er|tool)\b",
    re.IGNORECASE,
)
_SLIDER_TYPES = ("range",)
_UPLOAD_TYPES = ("file",)


def _interactivity(soup, js: str) -> Dict[str, Any]:
    """What a visitor can *do* on this page, not just read."""
    controls = soup.find_all(["input", "select", "textarea", "button"])
    kinds: Counter = Counter()
    for el in controls:
        if el.name == "input":
            kinds[(el.get("type") or "text").lower()] += 1
        else:
            kinds[el.name] += 1

    labels: List[str] = []
    for el in soup.find_all("label"):
        text = el.get_text(" ", strip=True)
        if text and text not in labels:
            labels.append(text[:70])
        if len(labels) >= 25:
            break

    from ..site_snapshot.extractor import is_interactive_container

    hidden_demos = [
        el
        for el in soup.find_all(attrs={"hidden": True})
        if is_interactive_container(el)
    ]
    named_demos = soup.select(
        "[class*=demo i],[id*=demo i],[class*=interactive i],[class*=widget i]"
    )
    demo_headings = [
        h.get_text(" ", strip=True)[:80]
        for h in soup.find_all(["h1", "h2", "h3"])
        if _DEMO_HEADING_RE.search(h.get_text(" ", strip=True) or "")
    ]

    listeners = Counter(m.lower() for m in _LISTENER_RE.findall(js))
    for el in soup.find_all(True):
        for attr in el.attrs:
            if attr.startswith("on") and len(attr) > 2:
                listeners[attr[2:].lower()] += 1
    profile = {
        "controls": len(controls),
        "control_types": dict(kinds.most_common()),
        "forms": len(soup.find_all("form")),
        "labels": labels,
        "buttons": kinds.get("button", 0) + kinds.get("submit", 0),
        "sliders": sum(kinds.get(t, 0) for t in _SLIDER_TYPES),
        "file_uploads": sum(kinds.get(t, 0) for t in _UPLOAD_TYPES),
        "demo_sections": demo_headings,
        "demo_containers": len(hidden_demos) + len(named_demos),
        # Demos that ship hidden and are revealed by their script: invisible to
        # any static extractor that treats [hidden] as chrome.
        "progressive_enhancement": bool(hidden_demos) and bool(_REVEAL_RE.search(js)),
        "event_listeners": dict(listeners.most_common(8)),
        "output_targets": len(soup.select("output, [id*=output i], [id*=result i]")),
    }
    profile["has_interactive_ui"] = bool(
        profile["controls"] or profile["demo_containers"] or demo_headings
    )
    profile["signals"] = _interactivity_signals(profile)
    return profile


def _interactivity_signals(p: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    if not p["has_interactive_ui"]:
        return ["no interactive UI detected"]
    if p["demo_sections"]:
        out.append("demo sections: " + ", ".join(p["demo_sections"][:3]))
    if p["controls"]:
        kinds = ", ".join(f"{n}x {k}" for k, n in list(p["control_types"].items())[:5])
        out.append(f"{p['controls']} controls ({kinds})")
    if p["file_uploads"]:
        out.append(
            f"{p['file_uploads']} file upload(s) — processes user files in-browser"
        )
    if p["sliders"]:
        out.append(f"{p['sliders']} slider(s)")
    if p["progressive_enhancement"]:
        out.append("demo ships hidden and is revealed by script (needs JS)")
    if p["event_listeners"]:
        out.append("listens for: " + ", ".join(list(p["event_listeners"])[:5]))
    return out


# --------------------------------------------------------------------------- #
# Scripts
# --------------------------------------------------------------------------- #
def _scripts(soup, scripts_ext, inline_scripts, haystack, js_text="") -> Dict[str, Any]:
    tags = soup.find_all("script")
    return {
        "external": [_short(s) for s in scripts_ext][:20],
        "external_count": len(scripts_ext),
        "inline_blocks": len(inline_scripts),
        "inline_bytes": sum(len(s) for s in inline_scripts),
        "external_bytes_analyzed": len(js_text),
        "async": sum(1 for s in tags if s.has_attr("async")),
        "defer": sum(1 for s in tags if s.has_attr("defer")),
        "modules": sum(1 for s in tags if (s.get("type") or "").lower() == "module"),
        "json_ld_blocks": sum(
            1 for s in tags if (s.get("type") or "").lower() == "application/ld+json"
        ),
        "frameworks": _match_libs(_JS_FRAMEWORKS, haystack),
    }


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _match_libs(table: Iterable[Tuple[str, str]], haystack: str) -> List[str]:
    return [name for name, pattern in table if re.search(pattern, haystack)]


def _class_sample(soup, limit: int = 400) -> str:
    """A bounded sample of class attributes — enough for utility-CSS detection."""
    classes: List[str] = []
    for el in soup.find_all(class_=True):
        classes.extend(el.get("class") or [])
        if len(classes) >= limit:
            break
    return " ".join(classes[:limit])


def _short(url: str, limit: int = 160) -> str:
    return url if len(url) <= limit else url[:limit] + "…"


def _soup(html: str):
    try:
        from bs4 import BeautifulSoup
    except Exception:  # pragma: no cover
        return None
    return BeautifulSoup(html or "", "html.parser")


def css_bundle(texts: Iterable[str], max_bytes: int = 2 * 1024 * 1024) -> str:
    """Concatenate stylesheet bodies up to a hard analysis ceiling."""
    out: List[str] = []
    total = 0
    for text in texts:
        if not text:
            continue
        if total + len(text) > max_bytes:
            out.append(text[: max(0, max_bytes - total)])
            break
        out.append(text)
        total += len(text)
    return "\n".join(out)
