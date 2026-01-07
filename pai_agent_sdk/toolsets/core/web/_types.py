"""Type definitions for web tools.

This module provides shared type definitions used across web tools.
"""

from typing import TypedDict


class SearchResult(TypedDict):
    """Single search result from web search."""

    title: str
    """Page title."""
    url: str
    """Page URL."""
    content: str
    """Snippet or description."""


class ImageSearchResult(TypedDict, total=False):
    """Single image search result."""

    url: str
    """Image URL."""
    thumbnail_url: str
    """Thumbnail URL (optional)."""
    title: str
    """Image title (optional)."""
    width: int
    """Image width in pixels (optional)."""
    height: int
    """Image height in pixels (optional)."""
    source: str
    """Source website (optional)."""


class HeadOnlyResult(TypedDict, total=False):
    """Result from HEAD request (head_only=True)."""

    exists: bool
    """Whether the resource exists."""
    accessible: bool
    """Whether the resource is accessible."""
    status_code: int
    """HTTP status code."""
    content_type: str | None
    """Content-Type header value."""
    content_length: str | None
    """Content-Length header value."""
    last_modified: str | None
    """Last-Modified header value."""
    url: str
    """Requested URL."""
    error: str
    """Error message if request failed."""


class FetchTextResult(TypedDict, total=False):
    """Result from GET request with text content."""

    content: str
    """Text content (possibly truncated)."""
    truncated: bool
    """Whether content was truncated."""
    total_length: int
    """Total content length before truncation."""
    tips: str
    """Usage tips."""


class ScrapeResult(TypedDict, total=False):
    """Result from web scraping."""

    success: bool
    """Whether scraping succeeded."""
    markdown_content: str
    """Scraped content as Markdown."""
    truncated: bool
    """Whether content was truncated."""
    total_length: int
    """Total content length before truncation."""
    tips: str
    """Usage tips."""
    error: str
    """Error message if scraping failed."""


class DownloadResult(TypedDict, total=False):
    """Result from file download."""

    success: bool
    """Whether download succeeded."""
    url: str
    """Source URL."""
    save_path: str
    """Local path where file was saved."""
    size: int
    """File size in bytes."""
    content_type: str
    """Content-Type of downloaded file."""
    message: str
    """Success message."""
    error: str
    """Error message if download failed."""


class ErrorResult(TypedDict):
    """Generic error result."""

    success: bool
    """Always False for errors."""
    error: str
    """Error message."""
