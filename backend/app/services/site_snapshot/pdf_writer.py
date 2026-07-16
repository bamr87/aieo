"""PDF generation with a guaranteed zero-dependency floor.

``render_text_pdf`` lays a plain-text report into a multi-page PDF using only
the standard library and the built-in Helvetica font — it adds NO dependency,
so PDF export works in CI and fully offline. ``try_reportlab`` and
``try_playwright`` are optional nicer upgrades used only when those packages
happen to be installed.

The stdlib writer computes real xref byte offsets from the serialized output
(not a running guess) and transcodes text to Latin-1 (Helvetica is WinAnsi-only)
so a stray emoji/CJK char degrades gracefully instead of corrupting the file.
"""

from __future__ import annotations

import textwrap
from typing import List, Optional

# US Letter, 1pt = 1/72 inch.
_PAGE_W, _PAGE_H = 612, 792
_MARGIN = 54
_FONT_SIZE = 9
_LEADING = 12
_CHARS_PER_LINE = 95  # conservative for Helvetica 9pt across the text width


def _pdf_escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _to_latin1(text: str) -> str:
    """Helvetica only encodes WinAnsi/Latin-1; replace anything else."""
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _wrap(lines: List[str]) -> List[str]:
    out: List[str] = []
    for raw in lines:
        raw = raw.replace("\t", "    ").rstrip("\n")
        if not raw:
            out.append("")
            continue
        wrapped = textwrap.wrap(
            raw,
            width=_CHARS_PER_LINE,
            replace_whitespace=False,
            drop_whitespace=False,
            break_long_words=True,
        )
        out.extend(wrapped or [""])
    return out


def _paginate(lines: List[str]) -> List[List[str]]:
    usable = _PAGE_H - 2 * _MARGIN
    per_page = max(1, int(usable // _LEADING))
    return [lines[i : i + per_page] for i in range(0, len(lines), per_page)] or [[""]]


def render_text_pdf(title: str, text: str) -> bytes:
    """Render plain text to a valid PDF using only the stdlib."""
    lines = _wrap([_to_latin1(line) for line in (title + "\n\n" + text).splitlines()])
    pages = _paginate(lines)

    # Object numbering: 1=Catalog, 2=Pages, 3=Font, then (page, content) pairs.
    objects: dict[int, bytes] = {}
    page_nums: List[int] = []
    next_num = 4
    for page_lines in pages:
        page_num = next_num
        content_num = next_num + 1
        page_nums.append(page_num)
        next_num += 2

        start_y = _PAGE_H - _MARGIN - _FONT_SIZE
        body = [
            "BT",
            f"/F1 {_FONT_SIZE} Tf",
            f"{_LEADING} TL",
            f"{_MARGIN} {start_y} Td",
        ]
        for line in page_lines:
            body.append(f"({_pdf_escape(line)}) Tj")
            body.append("T*")
        body.append("ET")
        stream = "\n".join(body).encode("latin-1", errors="replace")
        objects[content_num] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1")
            + stream
            + b"\nendstream"
        )
        objects[page_num] = (
            f"<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 {_PAGE_W} {_PAGE_H}] "
            f"/Resources << /Font << /F1 3 0 R >> >> "
            f"/Contents {content_num} 0 R >>"
        ).encode("latin-1")

    kids = " ".join(f"{n} 0 R" for n in page_nums)
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[2] = (f"<< /Type /Pages /Kids [{kids}] /Count {len(page_nums)} >>").encode(
        "latin-1"
    )
    objects[3] = (
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        b"/Encoding /WinAnsiEncoding >>"
    )

    # Serialize with accurate byte offsets.
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: dict[int, int] = {}
    total = len(objects)
    for num in range(1, total + 1):
        offsets[num] = len(out)
        out += f"{num} 0 obj\n".encode("latin-1")
        out += objects[num]
        out += b"\nendobj\n"

    xref_pos = len(out)
    out += f"xref\n0 {total + 1}\n".encode("latin-1")
    out += b"0000000000 65535 f \n"
    for num in range(1, total + 1):
        out += f"{offsets[num]:010d} 00000 n \n".encode("latin-1")
    out += (
        f"trailer\n<< /Size {total + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF"
    ).encode("latin-1")
    return bytes(out)


def try_reportlab(title: str, text: str) -> Optional[bytes]:
    try:
        import io

        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Preformatted, SimpleDocTemplate
    except Exception:
        return None
    try:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=letter, title=title)
        style = getSampleStyleSheet()["Code"]
        style.fontSize = 7
        style.leading = 9
        story = [Preformatted(chunk or " ", style) for chunk in text.split("\n\n")]
        doc.build(story)
        return buf.getvalue()
    except Exception:
        return None


def try_playwright(html: str) -> Optional[bytes]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_context().new_page()
            page.set_content(html, wait_until="load")
            data = page.pdf(format="A4", print_background=True)
            browser.close()
            return data
    except Exception:
        return None
