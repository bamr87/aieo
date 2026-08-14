"""Classifying the links a page carries: pages, downloads, media, data.

The snapshot crawler's URL normalizer already refuses the obvious asset
extensions (images, CSS, JS, archives), but a technical site's real payload is
often a file it never anticipated: ``ellipticcurve.py``, ``QrCode.java``,
``qrcodegen.ts``. Left unclassified those are treated as crawlable HTML pages —
270 of them on one real site — so the crawler wastes a request on each and then
records "not HTML", while the dataset never lists the downloads a reader
actually wants.

This module keeps one table of extensions and the two things callers need:
:func:`classify` (what kind of resource is this URL?) and :func:`is_resource`
(should the crawl frontier skip it?).
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

# extension -> (kind, language/format label)
_SOURCE_EXT = {
    "py": "Python",
    "java": "Java",
    "ts": "TypeScript",
    "tsx": "TypeScript",
    "js": "JavaScript",
    "mjs": "JavaScript",
    "jsx": "JavaScript",
    "c": "C",
    "h": "C",
    "cpp": "C++",
    "cxx": "C++",
    "cc": "C++",
    "hpp": "C++",
    "cs": "C#",
    "rs": "Rust",
    "go": "Go",
    "rb": "Ruby",
    "php": "PHP",
    "swift": "Swift",
    "kt": "Kotlin",
    "scala": "Scala",
    "hs": "Haskell",
    "ml": "OCaml",
    "lua": "Lua",
    "pl": "Perl",
    "r": "R",
    "m": "MATLAB",
    "sql": "SQL",
    "sh": "Shell",
    "bash": "Shell",
    "ps1": "PowerShell",
    "asm": "Assembly",
    "s": "Assembly",
    "vhd": "VHDL",
    "v": "Verilog",
    "ipynb": "Jupyter",
}
_ARCHIVE_EXT = {"zip", "gz", "tgz", "bz2", "xz", "7z", "rar", "tar"}
_DOC_EXT = {"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "odt", "epub"}
_DATA_EXT = {"json", "csv", "tsv", "xml", "yaml", "yml", "parquet", "sqlite", "db"}
_MEDIA_EXT = {
    "mp4": "video",
    "webm": "video",
    "mov": "video",
    "avi": "video",
    "mkv": "video",
    "mp3": "audio",
    "wav": "audio",
    "flac": "audio",
    "ogg": "audio",
    "m4a": "audio",
    "opus": "audio",
    "aac": "audio",
    "mid": "audio",
    "midi": "audio",
}
_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "svg", "webp", "avif", "ico", "bmp", "tiff"}
_FONT_EXT = {"woff", "woff2", "ttf", "otf", "eot"}

_EXT_RE = re.compile(r"\.([a-z0-9]{1,8})$", re.IGNORECASE)


def extension(url: str) -> Optional[str]:
    """Lowercased file extension of a URL path, or None."""
    path = urlparse(url).path or ""
    match = _EXT_RE.search(path)
    return match.group(1).lower() if match else None


def classify(url: str) -> Tuple[str, Optional[str]]:
    """Return ``(kind, label)`` for a URL.

    ``kind`` is one of ``page``, ``source``, ``archive``, ``document``, ``data``,
    ``video``, ``audio``, ``image`` or ``font``. ``label`` names the language or
    format where there is one to name (``"Python"``, ``"video"``).
    """
    ext = extension(url)
    if not ext:
        return "page", None
    if ext in _SOURCE_EXT:
        return "source", _SOURCE_EXT[ext]
    if ext in _ARCHIVE_EXT:
        return "archive", ext
    if ext in _DOC_EXT:
        return "document", ext
    if ext in _DATA_EXT:
        return "data", ext
    if ext in _MEDIA_EXT:
        return _MEDIA_EXT[ext], ext
    if ext in _IMAGE_EXT:
        return "image", ext
    if ext in _FONT_EXT:
        return "font", ext
    return "page", None


def is_resource(url: str) -> bool:
    """True when a URL is a file to record, not a page to crawl."""
    return classify(url)[0] != "page"


def split_links(links: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """Split extracted links into real page links and downloadable resources."""
    pages: List[Dict] = []
    resources: List[Dict] = []
    for link in links:
        url = link.get("url", "")
        kind, label = classify(url)
        if kind == "page":
            pages.append(link)
            continue
        resources.append(
            {
                "url": url,
                "type": kind,
                "format": label,
                "text": (link.get("text") or "")[:120] or None,
            }
        )
    return pages, resources
