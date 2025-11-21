"""
llms.txt generation service.

Generates llms.txt format (https://llmstxt.org/) from client pages.
Extracts metadata from HTML and creates a structured markdown document
optimized for LLM consumption.
"""
from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime
from html.parser import HTMLParser
import re

from app.models.base import SessionLocal
from app.models.client import Client, Page


class HTMLMetadataExtractor(HTMLParser):
    """Extract title and description from HTML."""

    def __init__(self):
        super().__init__()
        self.title = None
        self.description = None
        self.in_title = False
        self.title_content = []

        # Track meta tags
        self.meta_tags = {}

    def handle_starttag(self, tag, attrs):
        """Handle opening tags."""
        if tag == 'title':
            self.in_title = True
            self.title_content = []
        elif tag == 'meta':
            # Extract meta tag attributes
            attrs_dict = dict(attrs)
            if 'name' in attrs_dict and 'content' in attrs_dict:
                self.meta_tags[attrs_dict['name'].lower()] = attrs_dict['content']
            elif 'property' in attrs_dict and 'content' in attrs_dict:
                self.meta_tags[attrs_dict['property'].lower()] = attrs_dict['content']

    def handle_endtag(self, tag):
        """Handle closing tags."""
        if tag == 'title':
            self.in_title = False
            if self.title_content:
                self.title = ''.join(self.title_content).strip()

    def handle_data(self, data):
        """Handle text content."""
        if self.in_title:
            self.title_content.append(data)

    def get_metadata(self) -> Dict[str, Optional[str]]:
        """
        Get extracted metadata.

        Returns:
            Dictionary with 'title' and 'description' keys
        """
        # Try to get description from meta tags
        description = None

        # Priority order for description
        description_sources = [
            'description',
            'og:description',
            'twitter:description'
        ]

        for source in description_sources:
            if source in self.meta_tags:
                description = self.meta_tags[source]
                break

        return {
            'title': self.title,
            'description': description
        }


class LLMSTxtService:
    """Service for generating llms.txt files."""

    def __init__(self):
        """Initialize llms.txt service."""
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 3600  # 1 hour cache TTL

    def extract_page_metadata(self, page: Page) -> Dict[str, Optional[str]]:
        """
        Extract title and description from page's geo_html.

        Args:
            page: Page object with geo_html

        Returns:
            Dictionary with 'title', 'description', and 'url' keys
        """
        metadata = {
            'url': page.url,
            'title': None,
            'description': None
        }

        if not page.geo_html:
            return metadata

        # Parse HTML to extract metadata
        parser = HTMLMetadataExtractor()
        try:
            parser.feed(page.geo_html)
            extracted = parser.get_metadata()

            metadata['title'] = extracted['title']
            metadata['description'] = extracted['description']

        except Exception as e:
            print(f"[LLMSTxt] Error parsing HTML for {page.url}: {e}")
            # Fallback: use URL path as title
            metadata['title'] = self._url_to_title(page.url)

        # Fallback if no title found
        if not metadata['title']:
            metadata['title'] = self._url_to_title(page.url)

        return metadata

    def _url_to_title(self, url: str) -> str:
        """
        Convert URL to a readable title.

        Args:
            url: Page URL

        Returns:
            Readable title string
        """
        # Extract path from URL
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        path = parsed.path.strip('/')

        if not path:
            return "Homepage"

        # Convert path to title (e.g., "/products/shirt" -> "Products Shirt")
        parts = path.split('/')
        title_parts = []

        for part in parts:
            # Replace hyphens and underscores with spaces
            part = part.replace('-', ' ').replace('_', ' ')
            # Capitalize each word
            part = ' '.join(word.capitalize() for word in part.split())
            title_parts.append(part)

        return ' - '.join(title_parts)

    def _sort_pages(self, pages: List[Page]) -> List[Page]:
        """
        Sort pages for llms.txt output.

        Homepage first, then alphabetically by URL.

        Args:
            pages: List of pages

        Returns:
            Sorted list of pages
        """
        def sort_key(page):
            # Homepage first (path is just "/" or empty)
            import urllib.parse
            parsed = urllib.parse.urlparse(page.url)
            path = parsed.path.strip('/')

            if not path:
                return (0, page.url)  # Homepage
            else:
                return (1, page.url)  # Other pages sorted by URL

        return sorted(pages, key=sort_key)

    def _generate_site_description(self, client: Client, pages: List[Page]) -> str:
        """
        Generate site description for llms.txt.

        Args:
            client: Client object
            pages: List of pages

        Returns:
            Description string
        """
        # Simple description based on client domain
        domain = client.domain
        page_count = len(pages)

        description = f"AI-optimized content from {domain} with {page_count} page{'s' if page_count != 1 else ''}"

        return description

    def generate_for_client(self, client_id: UUID) -> Dict[str, any]:
        """
        Generate llms.txt for a client.

        Args:
            client_id: Client UUID

        Returns:
            Dictionary with 'llms_txt', 'page_count', and 'generated_at' keys

        Raises:
            ValueError: If client not found or has no pages
        """
        # Check cache
        cache_key = f"llms_txt_{client_id}"
        if cache_key in self.cache:
            cached_data, cached_at = self.cache[cache_key]
            # Check if cache is still valid
            age = (datetime.utcnow() - cached_at).total_seconds()
            if age < self.cache_ttl:
                print(f"[LLMSTxt] Returning cached result for {client_id} (age: {age:.1f}s)")
                return cached_data

        db = SessionLocal()
        try:
            # Get client
            client = db.query(Client).filter(Client.id == client_id).first()
            if not client:
                raise ValueError(f"Client not found: {client_id}")

            # Get all pages with geo_html (published pages)
            pages = db.query(Page).filter(
                Page.client_id == client_id,
                Page.geo_html.isnot(None)
            ).all()

            # Sort pages (homepage first, then alphabetically)
            pages = self._sort_pages(pages)

            # Generate llms.txt content
            lines = []

            # H1: Site name
            lines.append(f"# {client.name}")
            lines.append("")

            # Blockquote: Site description
            description = self._generate_site_description(client, pages)
            lines.append(f"> {description}")
            lines.append("")

            # H2: Pages section
            lines.append("## Pages")
            lines.append("")

            # List each page
            for page in pages:
                metadata = self.extract_page_metadata(page)

                title = metadata['title'] or 'Untitled'
                url = metadata['url']
                desc = metadata['description']

                # Format: "- Title: URL"
                lines.append(f"- {title}: {url}")

                # Add description if available (indented with 2 spaces)
                if desc:
                    # Truncate very long descriptions
                    if len(desc) > 300:
                        desc = desc[:297] + "..."
                    lines.append(f"  {desc}")

                lines.append("")

            # Join all lines
            llms_txt = '\n'.join(lines).rstrip() + '\n'

            result = {
                'llms_txt': llms_txt,
                'page_count': len(pages),
                'generated_at': datetime.utcnow().isoformat()
            }

            # Cache the result
            self.cache[cache_key] = (result, datetime.utcnow())

            return result

        finally:
            db.close()

    def invalidate_cache(self, client_id: UUID) -> None:
        """
        Invalidate cache for a client.

        Args:
            client_id: Client UUID
        """
        cache_key = f"llms_txt_{client_id}"
        if cache_key in self.cache:
            del self.cache[cache_key]
            print(f"[LLMSTxt] Cache invalidated for {client_id}")

    def get_cache_key(self, client_id: UUID) -> str:
        """
        Get cache key for a client.

        Args:
            client_id: Client UUID

        Returns:
            Cache key string
        """
        return f"llms_txt_{client_id}"


# Global service instance
llms_txt_service = LLMSTxtService()
