"""Generic parser for any web page."""

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from markdownify import markdownify as md

from .base import BaseParser, ParsedContent


class GenericParser(BaseParser):
    """Generic parser that works with any web page.

    Uses BeautifulSoup for HTML parsing and markdownify for
    converting HTML to Markdown.
    """

    # Elements to remove before parsing
    REMOVE_SELECTORS = [
        "script",
        "style",
        "nav",
        "header",
        "footer",
        "aside",
        "iframe",
        "noscript",
        ".ad",
        ".ads",
        ".advertisement",
        ".sidebar",
        ".comments",
        ".comment",
        ".social-share",
        ".related-posts",
        "[role='navigation']",
        "[role='banner']",
        "[role='complementary']",
    ]

    # Priority selectors for main content (in order)
    CONTENT_SELECTORS = [
        "article",
        "[role='main']",
        "main",
        ".post-content",
        ".article-content",
        ".entry-content",
        ".content",
        "#content",
        ".post",
        ".article",
    ]

    @property
    def name(self) -> str:
        return "generic"

    @property
    def source_type(self) -> str:
        return "web"

    def can_parse(self, url: str) -> bool:
        """Generic parser can handle any URL."""
        return True

    def parse(self, html: str, url: str) -> ParsedContent:
        """Parse HTML and extract content as Markdown.

        Args:
            html: Raw HTML content.
            url: Source URL.

        Returns:
            ParsedContent with title and Markdown content.
        """
        soup = BeautifulSoup(html, "lxml")

        # Remove unwanted elements
        self._remove_elements(soup)

        # Extract title
        title = self._extract_title(soup)

        # Extract main content
        content_html = self._extract_content(soup)

        # Convert to Markdown
        content_md = self._html_to_markdown(content_html)

        # Clean up Markdown
        content_md = self._clean_markdown(content_md)

        # Extract author if available
        author = self._extract_author(soup)

        # Extract published date if available
        published_at = self._extract_date(soup)

        return ParsedContent(
            title=title,
            content=content_md,
            url=url,
            source_id=self.generate_source_id(url),
            source_type=self.source_type,
            author=author,
            published_at=published_at,
            metadata={
                "parser": self.name,
                "domain": urlparse(url).netloc,
            },
        )

    def _remove_elements(self, soup: BeautifulSoup) -> None:
        """Remove unwanted elements from soup."""
        for selector in self.REMOVE_SELECTORS:
            for element in soup.select(selector):
                element.decompose()

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        # Try og:title first
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()

        # Try h1
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        # Try title tag
        title = soup.find("title")
        if title:
            return title.get_text(strip=True)

        return "Untitled"

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main content HTML."""
        # Try priority selectors
        for selector in self.CONTENT_SELECTORS:
            content = soup.select_one(selector)
            if content:
                return str(content)

        # Fallback to body
        body = soup.find("body")
        if body:
            return str(body)

        return str(soup)

    def _html_to_markdown(self, html: str) -> str:
        """Convert HTML to Markdown."""
        return md(
            html,
            heading_style="atx",
            bullets="-",
            code_language_callback=lambda el: el.get("class", [""])[0]
            if el.get("class")
            else "",
        )

    def _clean_markdown(self, content: str) -> str:
        """Clean up Markdown content."""
        # Remove excessive newlines
        content = re.sub(r"\n{3,}", "\n\n", content)

        # Remove leading/trailing whitespace
        content = content.strip()

        # Remove empty links
        content = re.sub(r"\[]\([^)]*\)", "", content)

        # Remove image-only lines if they're broken
        content = re.sub(r"!\[\]\(\)", "", content)

        return content

    def _extract_author(self, soup: BeautifulSoup) -> str | None:
        """Extract author from meta tags or common elements."""
        # Try meta author
        author_meta = soup.find("meta", attrs={"name": "author"})
        if author_meta and author_meta.get("content"):
            return author_meta["content"].strip()

        # Try article:author
        author_og = soup.find("meta", property="article:author")
        if author_og and author_og.get("content"):
            return author_og["content"].strip()

        # Try common class names
        for selector in [".author", ".byline", "[rel='author']"]:
            author_el = soup.select_one(selector)
            if author_el:
                return author_el.get_text(strip=True)

        return None

    def _extract_date(self, soup: BeautifulSoup) -> str | None:
        """Extract publication date."""
        # Try article:published_time
        date_meta = soup.find("meta", property="article:published_time")
        if date_meta and date_meta.get("content"):
            return date_meta["content"]

        # Try time element
        time_el = soup.find("time")
        if time_el and time_el.get("datetime"):
            return time_el["datetime"]

        return None
