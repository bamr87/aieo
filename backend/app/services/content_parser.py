"""Content parsing service for markdown and HTML."""

import hashlib
from typing import Dict, List
from bs4 import BeautifulSoup
import markdown
import html2text


class ContentParser:
    """Parse and extract content from various formats."""

    def __init__(self):
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = False

    def parse(self, content: str, format: str = "markdown") -> Dict:
        """
        Parse content and extract structured information.

        Args:
            content: Raw content string
            format: Content format ('markdown' or 'html')

        Returns:
            Dictionary with parsed content structure
        """
        if format == "html":
            # Convert HTML to markdown first
            markdown_content = self.html_converter.handle(content)
            html_soup = BeautifulSoup(content, "html.parser")
        else:
            markdown_content = content
            html_soup = None

        # Parse markdown
        md = markdown.Markdown(extensions=["tables", "fenced_code", "nl2br"])
        html_from_md = md.convert(markdown_content)

        if html_soup is None:
            html_soup = BeautifulSoup(html_from_md, "html.parser")

        # Extract components
        result = {
            "text": self._extract_text(html_soup),
            "headers": self._extract_headers(html_soup),
            "tables": self._extract_tables(html_soup),
            "lists": self._extract_lists(html_soup),
            "links": self._extract_links(html_soup),
            "word_count": len(markdown_content.split()),
            "char_count": len(markdown_content),
            "content_hash": self._hash_content(content),
        }

        return result

    def _extract_text(self, soup: BeautifulSoup) -> str:
        """Extract plain text from HTML."""
        return soup.get_text(separator=" ", strip=True)

    def _extract_headers(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract headers with their levels."""
        headers = []
        for i in range(1, 7):
            for header in soup.find_all(f"h{i}"):
                headers.append(
                    {
                        "level": i,
                        "text": header.get_text(strip=True),
                        "position": len(headers),
                    }
                )
        return headers

    def _extract_tables(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract tables from HTML."""
        tables = []
        for table in soup.find_all("table"):
            rows = []
            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if cells:
                    rows.append(cells)
            if rows:
                tables.append(
                    {
                        "rows": rows,
                        "column_count": max(len(row) for row in rows) if rows else 0,
                        "row_count": len(rows),
                    }
                )
        return tables

    def _extract_lists(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract ordered and unordered lists."""
        lists = []
        for ul in soup.find_all(["ul", "ol"]):
            items = [li.get_text(strip=True) for li in ul.find_all("li")]
            if items:
                lists.append(
                    {
                        "type": "ordered" if ul.name == "ol" else "unordered",
                        "items": items,
                        "item_count": len(items),
                    }
                )
        return lists

    def _extract_links(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract links from HTML."""
        links = []
        for a in soup.find_all("a", href=True):
            links.append(
                {
                    "text": a.get_text(strip=True),
                    "url": a["href"],
                }
            )
        return links

    def _hash_content(self, content: str) -> str:
        """Generate SHA256 hash of content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
