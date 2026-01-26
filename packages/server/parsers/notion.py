"""Notion page parser for extracting content and sub-pages."""

import re
from urllib.parse import urlparse, unquote

from bs4 import BeautifulSoup, Tag

from .base import BaseParser, ParsedContent


class NotionParser(BaseParser):
    """Parser for Notion pages."""

    # Notion URL patterns
    NOTION_DOMAINS = ["notion.so", "notion.site", "www.notion.so"]
    PAGE_ID_PATTERN = re.compile(r"([a-f0-9]{32}|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})")

    @property
    def name(self) -> str:
        return "NotionParser"

    @property
    def source_type(self) -> str:
        return "notion"

    def can_parse(self, url: str) -> bool:
        """Check if URL is a Notion page."""
        try:
            parsed = urlparse(url)
            return any(domain in parsed.netloc for domain in self.NOTION_DOMAINS)
        except Exception:
            return False

    def parse(self, html: str, url: str) -> ParsedContent:
        """Parse Notion page HTML and extract content.

        Args:
            html: Raw HTML content from Notion page.
            url: Source URL.

        Returns:
            ParsedContent with extracted data.
        """
        soup = BeautifulSoup(html, "html.parser")

        # Extract page ID
        page_id = self.get_page_id(url)
        source_id = page_id if page_id else self.generate_source_id(url)

        # Extract title
        title = self._extract_title(soup)

        # Extract main content
        content = self._extract_content(soup)

        # Extract sub-pages
        sub_pages = self.extract_sub_pages(html, url)

        return ParsedContent(
            title=title,
            content=content,
            url=url,
            source_id=source_id,
            source_type=self.source_type,
            sub_pages=sub_pages,
            metadata={
                "page_id": page_id,
                "has_sub_pages": len(sub_pages) > 0,
            },
        )

    def get_page_id(self, url: str) -> str | None:
        """Extract Notion page ID from URL.

        Notion URLs can have formats:
        - notion.so/Page-Name-abc123def456...
        - notion.so/workspace/Page-Name-abc123def456...
        - notion.site/Page-Name-abc123def456...
        - With or without dashes in the 32-char ID

        Args:
            url: Notion page URL.

        Returns:
            32-character page ID (without dashes) or None.
        """
        try:
            parsed = urlparse(url)
            path = unquote(parsed.path)

            # Try to find page ID in path
            match = self.PAGE_ID_PATTERN.search(path)
            if match:
                page_id = match.group(1).replace("-", "")
                return page_id

            # Try fragment (for some Notion URLs)
            if parsed.fragment:
                match = self.PAGE_ID_PATTERN.search(parsed.fragment)
                if match:
                    return match.group(1).replace("-", "")

            return None
        except Exception:
            return None

    def format_page_id_as_uuid(self, page_id: str) -> str:
        """Format 32-char page ID as UUID format.

        Args:
            page_id: 32-character page ID.

        Returns:
            UUID formatted string (8-4-4-4-12).
        """
        if len(page_id) != 32:
            return page_id

        return f"{page_id[:8]}-{page_id[8:12]}-{page_id[12:16]}-{page_id[16:20]}-{page_id[20:]}"

    def extract_sub_pages(self, html: str, url: str) -> list[dict[str, str]]:
        """Extract sub-page links from Notion page.

        Args:
            html: Raw HTML content.
            url: Source URL for resolving relative links.

        Returns:
            List of sub-page info with 'url', 'title', 'id' keys.
        """
        soup = BeautifulSoup(html, "html.parser")
        sub_pages = []
        seen_ids = set()

        # Method 1: Find links that look like Notion pages
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")

            # Check if it's a Notion link
            if not self._is_notion_link(href):
                continue

            # Extract page ID
            page_id = self.get_page_id(href)
            if not page_id or page_id in seen_ids:
                continue

            # Skip if it's the same page
            current_id = self.get_page_id(url)
            if page_id == current_id:
                continue

            seen_ids.add(page_id)

            # Get title from link text or aria-label
            title = self._get_link_title(link)

            sub_pages.append({
                "url": self._normalize_notion_url(href),
                "title": title,
                "id": page_id,
            })

        # Method 2: Find Notion-specific page blocks
        for block in soup.find_all(attrs={"data-block-id": True}):
            if not self._is_page_block(block):
                continue

            block_id = block.get("data-block-id", "").replace("-", "")
            if block_id in seen_ids or len(block_id) != 32:
                continue

            # Skip if it's the same page
            current_id = self.get_page_id(url)
            if block_id == current_id:
                continue

            seen_ids.add(block_id)

            title = self._extract_block_title(block)
            sub_url = f"https://notion.so/{block_id}"

            sub_pages.append({
                "url": sub_url,
                "title": title,
                "id": block_id,
            })

        return sub_pages

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title from Notion HTML."""
        # Try Notion-specific title element
        title_elem = soup.find(class_=re.compile(r"notion-page-block|notion-title"))
        if title_elem:
            return title_elem.get_text(strip=True)

        # Try page header
        header = soup.find(attrs={"data-block-id": True, "data-content-editable-leaf": "true"})
        if header:
            text = header.get_text(strip=True)
            if text:
                return text

        # Try h1
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        # Try title tag
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)
            # Remove " | Notion" suffix
            title = re.sub(r"\s*\|\s*Notion\s*$", "", title)
            return title

        return "Untitled"

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from Notion page and convert to Markdown."""
        content_parts = []

        # Find the main content area
        main_content = soup.find(class_=re.compile(r"notion-page-content|notion-scroller"))
        if not main_content:
            main_content = soup.find("article") or soup.find("main") or soup.body

        if not main_content:
            return ""

        # Process each block
        for block in self._find_content_blocks(main_content):
            markdown = self._block_to_markdown(block)
            if markdown:
                content_parts.append(markdown)

        return "\n\n".join(content_parts)

    def _find_content_blocks(self, container: Tag) -> list[Tag]:
        """Find all content blocks in the container."""
        blocks = []

        # Find blocks with data-block-id attribute
        for block in container.find_all(attrs={"data-block-id": True}):
            # Skip nested blocks (will be handled by parent)
            parent = block.find_parent(attrs={"data-block-id": True})
            if parent and parent in blocks:
                continue
            blocks.append(block)

        # If no Notion-specific blocks found, use general elements
        if not blocks:
            for elem in container.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "pre", "blockquote"]):
                blocks.append(elem)

        return blocks

    def _block_to_markdown(self, block: Tag) -> str:
        """Convert a Notion block to Markdown."""
        # Determine block type
        block_class = " ".join(block.get("class", []))

        # Header blocks
        if "notion-header-block" in block_class or block.name == "h1":
            return f"# {block.get_text(strip=True)}"
        elif "notion-sub_header-block" in block_class or block.name == "h2":
            return f"## {block.get_text(strip=True)}"
        elif "notion-sub_sub_header-block" in block_class or block.name == "h3":
            return f"### {block.get_text(strip=True)}"

        # Code block
        if "notion-code-block" in block_class or block.name == "pre":
            code = block.find("code") or block
            language = self._detect_code_language(block)
            code_text = code.get_text()
            return f"```{language}\n{code_text}\n```"

        # Quote/Callout block
        if "notion-quote-block" in block_class or "notion-callout-block" in block_class or block.name == "blockquote":
            text = block.get_text(strip=True)
            lines = text.split("\n")
            return "\n".join(f"> {line}" for line in lines)

        # Toggle block
        if "notion-toggle-block" in block_class:
            summary = block.find(class_=re.compile(r"toggle|summary"))
            summary_text = summary.get_text(strip=True) if summary else ""
            content = block.find(class_=re.compile(r"toggle-content|indented"))
            content_text = content.get_text(strip=True) if content else ""
            return f"<details>\n<summary>{summary_text}</summary>\n\n{content_text}\n</details>"

        # Bulleted list
        if "notion-bulleted_list-block" in block_class or block.name == "ul":
            items = block.find_all("li") if block.name == "ul" else [block]
            return "\n".join(f"- {item.get_text(strip=True)}" for item in items)

        # Numbered list
        if "notion-numbered_list-block" in block_class or block.name == "ol":
            items = block.find_all("li") if block.name == "ol" else [block]
            return "\n".join(f"{i+1}. {item.get_text(strip=True)}" for i, item in enumerate(items))

        # To-do block
        if "notion-to_do-block" in block_class:
            checkbox = block.find("input", {"type": "checkbox"})
            checked = checkbox.get("checked") if checkbox else False
            text = block.get_text(strip=True)
            marker = "[x]" if checked else "[ ]"
            return f"- {marker} {text}"

        # Divider
        if "notion-divider-block" in block_class or block.name == "hr":
            return "---"

        # Image block
        if "notion-image-block" in block_class:
            img = block.find("img")
            if img:
                src = img.get("src", "")
                alt = img.get("alt", "image")
                return f"![{alt}]({src})"

        # Default: paragraph or text block
        text = block.get_text(strip=True)
        if text:
            return text

        return ""

    def _detect_code_language(self, block: Tag) -> str:
        """Detect programming language from code block."""
        # Try class name
        code = block.find("code")
        if code:
            classes = code.get("class", [])
            for cls in classes:
                if cls.startswith("language-"):
                    return cls.replace("language-", "")

        # Try data attribute
        lang = block.get("data-language") or block.get("data-code-language")
        if lang:
            return lang

        return ""

    def _is_notion_link(self, href: str) -> bool:
        """Check if href is a Notion page link."""
        if not href:
            return False

        try:
            parsed = urlparse(href)
            # Check for Notion domains
            if any(domain in parsed.netloc for domain in self.NOTION_DOMAINS):
                return True
            # Check for relative Notion links (starts with /)
            if href.startswith("/") and self.PAGE_ID_PATTERN.search(href):
                return True
            return False
        except Exception:
            return False

    def _normalize_notion_url(self, href: str) -> str:
        """Normalize Notion URL to full format."""
        if href.startswith("/"):
            return f"https://notion.so{href}"
        return href

    def _get_link_title(self, link: Tag) -> str:
        """Extract title from link element."""
        # Try aria-label
        aria_label = link.get("aria-label")
        if aria_label:
            return aria_label

        # Try text content
        text = link.get_text(strip=True)
        if text:
            return text

        # Try title attribute
        title = link.get("title")
        if title:
            return title

        return "Untitled"

    def _is_page_block(self, block: Tag) -> bool:
        """Check if block is a page/subpage block."""
        block_class = " ".join(block.get("class", []))
        return any(pattern in block_class for pattern in [
            "notion-page-block",
            "notion-child_page-block",
            "notion-link-to-page-block",
        ])

    def _extract_block_title(self, block: Tag) -> str:
        """Extract title from a page block."""
        # Try finding title element within block
        title_elem = block.find(class_=re.compile(r"title|page-title"))
        if title_elem:
            return title_elem.get_text(strip=True)

        # Try text content
        text = block.get_text(strip=True)
        if text:
            return text

        return "Untitled"
