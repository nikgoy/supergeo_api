"""
Sitemap parsing service.

Parses XML sitemaps and extracts URLs for caching using ultimate-sitemap-parser library.
Supports both regular sitemaps and sitemap index files with robust error handling.
"""
from typing import List, Dict
from urllib.parse import urlparse
import time

from usp.fetch_parse import SitemapFetcher

from app.config import settings


class SitemapParser:
    """Service for parsing XML sitemaps using ultimate-sitemap-parser."""

    def __init__(self, timeout: int = 30, max_urls: int = 10000):
        """
        Initialize sitemap parser.

        Args:
            timeout: Timeout for HTTP requests in seconds (passed to usp)
            max_urls: Maximum number of URLs to parse (safety limit)
        """
        self.timeout = timeout
        self.max_urls = max_urls

    def parse_sitemap_recursive(self, url: str, max_depth: int = 3, track_errors: bool = False) -> List[Dict]:
        """
        Parse sitemap recursively, following sitemap index references.

        Args:
            url: Sitemap URL (can be index or regular)
            max_depth: Maximum recursion depth (Note: usp handles this internally)
            track_errors: If True, collect error information (use parse_sitemap_recursive_detailed instead)

        Returns:
            List of all URLs found

        Raises:
            ValueError: If max_urls limit is exceeded
        """
        result = self.parse_sitemap_recursive_detailed(url, max_depth)
        return result['urls']

    def parse_sitemap_recursive_detailed(self, url: str, max_depth: int = 3) -> Dict:
        """
        Parse sitemap recursively with detailed error tracking using ultimate-sitemap-parser.

        Args:
            url: Sitemap URL (can be index or regular)
            max_depth: Maximum recursion depth (Note: usp library handles depth internally)

        Returns:
            Dictionary with 'urls', 'errors', 'visited_sitemaps' keys

        Raises:
            ValueError: If max_urls limit is exceeded
        """
        all_urls = []
        visited_sitemaps = set()
        errors = []

        print(f"[Sitemap] Starting recursive parse of: {url}")

        try:
            # Validate URL format
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(f"Invalid URL: {url}")

            # Use SitemapFetcher directly with the sitemap URL
            # This is more direct than sitemap_tree_for_homepage() which expects homepage URLs
            # It handles: retries, gzip compression, relative URLs, namespaces, etc.
            print(f"[Sitemap] Fetching sitemap at recursion level 0")
            fetcher = SitemapFetcher(url, recursion_level=0)
            tree = fetcher.sitemap()

            # Track which sitemaps were visited
            visited_sitemaps.add(url)

            # Recursively collect all sitemaps in the tree
            def collect_sitemaps(sitemap, depth=0):
                """Recursively collect all sitemap URLs from the tree"""
                if hasattr(sitemap, 'url') and sitemap.url:
                    visited_sitemaps.add(sitemap.url)

                if hasattr(sitemap, 'sub_sitemaps') and sitemap.sub_sitemaps:
                    for sub in sitemap.sub_sitemaps:
                        collect_sitemaps(sub, depth + 1)

            collect_sitemaps(tree)

            # Extract all pages from the tree
            page_count = 0
            for page in tree.all_pages():
                # Convert page object to dictionary format
                url_data = {'loc': page.url}

                # Add optional metadata if available (convert to JSON-serializable types)
                if page.last_modified:
                    url_data['lastmod'] = page.last_modified.isoformat() if hasattr(page.last_modified, 'isoformat') else str(page.last_modified)

                if page.priority is not None:
                    url_data['priority'] = str(page.priority)

                if page.change_frequency:
                    # Convert enum to string (e.g., SitemapPageChangeFrequency.DAILY -> "daily")
                    url_data['changefreq'] = str(page.change_frequency.value) if hasattr(page.change_frequency, 'value') else str(page.change_frequency)

                all_urls.append(url_data)
                page_count += 1

                # Check limit
                if len(all_urls) > self.max_urls:
                    error_msg = f"Exceeded maximum URL limit ({self.max_urls})"
                    print(f"[Sitemap] {error_msg}")
                    raise ValueError(error_msg)

            print(f"[Sitemap] Successfully parsed {page_count} URLs from sitemap tree")
            print(f"[Sitemap] Visited {len(visited_sitemaps)} sitemaps total")

        except ValueError as e:
            # Re-raise ValueError (max URLs, invalid URL)
            raise

        except Exception as e:
            error_msg = str(e)
            print(f"[Sitemap] Error parsing {url}: {error_msg}")
            errors.append({
                'url': url,
                'error': error_msg,
                'depth': 0
            })

            # If we got no URLs and have an error, this is a complete failure
            if not all_urls:
                # Try to provide helpful error message
                if "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
                    raise Exception(f"Timeout fetching sitemap: {error_msg}")
                elif "403" in error_msg or "forbidden" in error_msg.lower():
                    raise Exception(f"Access forbidden (403): The website is blocking the request")
                elif "404" in error_msg or "not found" in error_msg.lower():
                    raise Exception(f"Sitemap not found (404): {url}")
                else:
                    raise Exception(f"Failed to parse sitemap: {error_msg}")

        return {
            'urls': all_urls,
            'errors': errors,
            'visited_sitemaps': list(visited_sitemaps),
            'total_sitemaps': len(visited_sitemaps),
            'total_urls': len(all_urls),
            'has_errors': len(errors) > 0
        }

    def fetch_sitemap(self, url: str, max_retries: int = 3) -> str:
        """
        Fetch sitemap content from URL (kept for backward compatibility).

        Note: This method is now a thin wrapper. For recursive parsing,
        use parse_sitemap_recursive_detailed which uses ultimate-sitemap-parser
        internally and handles retries, compression, etc.

        Args:
            url: Sitemap URL
            max_retries: Maximum number of retries (unused, kept for compatibility)

        Returns:
            Sitemap XML content as string

        Raises:
            Exception: If fetch fails
        """
        import requests

        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL: {url}")

        try:
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={
                    'User-Agent': 'AI-Cache-Layer/1.0 (Sitemap Parser)'
                }
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            raise Exception(f"Failed to fetch sitemap: {str(e)}")

    def parse_sitemap(self, content: str, is_index: bool = None) -> Dict:
        """
        Parse sitemap XML content (kept for backward compatibility).

        Note: For production use, prefer parse_sitemap_recursive_detailed
        which uses ultimate-sitemap-parser for better reliability.

        Args:
            content: XML sitemap content
            is_index: Whether this is a sitemap index (auto-detected)

        Returns:
            Dictionary with 'urls' and/or 'sitemaps' keys
        """
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML sitemap: {e}")

        result = {'urls': [], 'sitemaps': []}

        # Check if this is a sitemap index
        is_index = root.tag.endswith('sitemapindex')

        SITEMAP_NS = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

        if is_index:
            # Parse sitemap index
            for sitemap in root.findall('.//sm:sitemap', SITEMAP_NS):
                loc = sitemap.find('sm:loc', SITEMAP_NS)
                if loc is not None and loc.text:
                    result['sitemaps'].append(loc.text.strip())

            # Fallback without namespace
            if not result['sitemaps']:
                for sitemap in root.findall('.//sitemap'):
                    loc = sitemap.find('loc')
                    if loc is not None and loc.text:
                        result['sitemaps'].append(loc.text.strip())
        else:
            # Parse regular sitemap URLs
            for url_elem in root.findall('.//sm:url', SITEMAP_NS):
                loc = url_elem.find('sm:loc', SITEMAP_NS)
                if loc is not None and loc.text:
                    url_data = {'loc': loc.text.strip()}

                    # Extract optional fields
                    for field in ['lastmod', 'changefreq', 'priority']:
                        elem = url_elem.find(f'sm:{field}', SITEMAP_NS)
                        if elem is not None and elem.text:
                            url_data[field] = elem.text.strip()

                    result['urls'].append(url_data)

            # Fallback without namespace
            if not result['urls']:
                for url_elem in root.findall('.//url'):
                    loc = url_elem.find('loc')
                    if loc is not None and loc.text:
                        url_data = {'loc': loc.text.strip()}

                        for field in ['lastmod', 'changefreq', 'priority']:
                            elem = url_elem.find(field)
                            if elem is not None and elem.text:
                                url_data[field] = elem.text.strip()

                        result['urls'].append(url_data)

        return result


# Global sitemap parser instance
sitemap_parser = SitemapParser(
    timeout=settings.page_timeout,
    max_urls=10000
)
