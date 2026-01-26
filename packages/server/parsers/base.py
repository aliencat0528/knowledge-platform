"""Base parser interface for content extraction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedContent:
    """Result of parsing a page."""

    title: str
    content: str  # Markdown format
    url: str
    source_id: str
    source_type: str = "web"
    author: str | None = None
    published_at: str | None = None
    tags: list[str] = field(default_factory=list)
    sub_pages: list[dict[str, str]] = field(default_factory=list)  # For tree parsing
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseParser(ABC):
    """Abstract base class for content parsers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Parser name for identification."""
        pass

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Source type this parser handles."""
        pass

    @abstractmethod
    def can_parse(self, url: str) -> bool:
        """Check if this parser can handle the given URL.

        Args:
            url: The URL to check.

        Returns:
            True if this parser can handle the URL.
        """
        pass

    @abstractmethod
    def parse(self, html: str, url: str) -> ParsedContent:
        """Parse HTML content and extract article data.

        Args:
            html: Raw HTML content.
            url: Source URL.

        Returns:
            ParsedContent with extracted data.
        """
        pass

    def generate_source_id(self, url: str) -> str:
        """Generate a unique source ID from URL.

        Args:
            url: The source URL.

        Returns:
            A unique identifier string.
        """
        import hashlib

        return hashlib.md5(url.encode()).hexdigest()

    def extract_sub_pages(self, html: str, url: str) -> list[dict[str, str]]:
        """Extract sub-page links from HTML.

        Override in subclasses for site-specific logic.

        Args:
            html: Raw HTML content.
            url: Source URL.

        Returns:
            List of sub-page info dicts with 'url', 'title', 'id' keys.
        """
        return []
