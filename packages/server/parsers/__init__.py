"""Content parsers package."""

from .base import BaseParser, ParsedContent
from .generic import GenericParser
from .notion import NotionParser

# Registry of all available parsers
# Order matters: more specific parsers should come first
PARSERS: list[BaseParser] = [
    NotionParser(),
    GenericParser(),  # Fallback parser
]


def get_parser_for_url(url: str) -> BaseParser:
    """Get the appropriate parser for a given URL.

    Args:
        url: The URL to find a parser for.

    Returns:
        The first parser that can handle the URL.
    """
    for parser in PARSERS:
        if parser.can_parse(url):
            return parser

    # Return generic parser as fallback
    return GenericParser()


__all__ = [
    "BaseParser",
    "ParsedContent",
    "GenericParser",
    "NotionParser",
    "PARSERS",
    "get_parser_for_url",
]
