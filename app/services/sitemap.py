"""
Sitemap parsing service.

Parses XML sitemaps and extracts URLs for caching.
Supports both regular sitemaps and sitemap index files.
"""
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from datetime import datetime
import requests
from urllib.parse import urljoin, urlparse
import time

from app.config import settings


class SitemapParser:
    """Service for parsing XML sitemaps."""

    # XML namespaces
    SITEMAP_NS = {
        'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9',
        'image': 'http://www.google.com/schemas/sitemap-image/1.1',
        'news': 'http://www.google.com/schemas/sitemap-news/0.9',
        'video': 'http://www.google.com/schemas/sitemap-video/1.1',
    }

    def __init__(self, timeout: int = 30, max_urls: int = 10000):
        """
        Initialize sitemap parser.

        Args:
            timeout: Timeout for HTTP requests in seconds
            max_urls: Maximum number of URLs to parse (safety limit)
        """
        self.timeout = timeout
        self.max_urls = max_urls

    def fetch_sitemap(self, url: str, max_retries: int = 3) -> str:
        """
        Fetch sitemap content from URL with retry logic.

        Args:
            url: Sitemap URL
            max_retries: Maximum number of retries for transient errors

        Returns:
            Sitemap XML content as string

        Raises:
            requests.RequestException: If fetch fails after retries
            ValueError: If URL is invalid
        """
        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL: {url}")

        last_exception = None

        for attempt in range(max_retries):
            try:
                # Fetch with timeout
                response = requests.get(
                    url,
                    timeout=self.timeout,
                    headers={
                        'User-Agent': 'AI-Cache-Layer/1.0 (Sitemap Parser)'
                    }
                )
                response.raise_for_status()
                return response.text

            except requests.exceptions.HTTPError as e:
                # Retry on 5xx errors and 429 (rate limit)
                if e.response is not None and e.response.status_code in [429, 500, 502, 503, 504]:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                        print(f"[Sitemap] HTTP {e.response.status_code} for {url}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                # Don't retry on 4xx errors (except 429)
                raise

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                # Retry on network errors
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"[Sitemap] Network error for {url}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                raise

        # If we get here, all retries failed
        raise last_exception

    def parse_sitemap(self, content: str, is_index: bool = None) -> Dict[str, List[Dict]]:
        """
        Parse sitemap XML content.

        Args:
            content: XML sitemap content
            is_index: Whether this is a sitemap index (auto-detected if None)

        Returns:
            Dictionary with 'urls' and/or 'sitemaps' keys

        Example return:
            {
                'urls': [
                    {'loc': 'https://example.com/page1', 'lastmod': '2024-01-01', 'priority': '0.8'},
                    ...
                ],
                'sitemaps': ['https://example.com/sitemap2.xml']
            }
        """
        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML sitemap: {e}")

        result = {'urls': [], 'sitemaps': []}

        # Detect if this is a sitemap index
        if is_index is None:
            is_index = self._is_sitemap_index(root)

        if is_index:
            # Parse sitemap index
            result['sitemaps'] = self._parse_sitemap_index(root)
        else:
            # Parse regular sitemap
            result['urls'] = self._parse_url_set(root)

        return result

    def _is_sitemap_index(self, root: ET.Element) -> bool:
        """
        Check if XML is a sitemap index.

        Args:
            root: XML root element

        Returns:
            True if sitemap index, False if regular sitemap
        """
        # Check for <sitemapindex> tag
        if root.tag.endswith('sitemapindex'):
            return True

        # Check for <sitemap> children (index contains <sitemap>, regular contains <url>)
        for ns in ['', '{http://www.sitemaps.org/schemas/sitemap/0.9}']:
            if root.find(f'{ns}sitemap') is not None:
                return True

        return False

    def _parse_sitemap_index(self, root: ET.Element) -> List[str]:
        """
        Parse sitemap index and extract sitemap URLs.

        Args:
            root: XML root element

        Returns:
            List of sitemap URLs
        """
        sitemaps = []

        # Try with and without namespace
        for sitemap in root.findall('.//sm:sitemap', self.SITEMAP_NS):
            loc = sitemap.find('sm:loc', self.SITEMAP_NS)
            if loc is not None and loc.text:
                sitemaps.append(loc.text.strip())

        # Fallback without namespace
        if not sitemaps:
            for sitemap in root.findall('.//sitemap'):
                loc = sitemap.find('loc')
                if loc is not None and loc.text:
                    sitemaps.append(loc.text.strip())

        return sitemaps

    def _parse_url_set(self, root: ET.Element) -> List[Dict]:
        """
        Parse URL set from sitemap.

        Args:
            root: XML root element

        Returns:
            List of URL dictionaries
        """
        urls = []

        # Try with namespace
        for url_elem in root.findall('.//sm:url', self.SITEMAP_NS):
            url_data = self._extract_url_data(url_elem, with_ns=True)
            if url_data:
                urls.append(url_data)

        # Fallback without namespace
        if not urls:
            for url_elem in root.findall('.//url'):
                url_data = self._extract_url_data(url_elem, with_ns=False)
                if url_data:
                    urls.append(url_data)

        return urls

    def _extract_url_data(self, url_elem: ET.Element, with_ns: bool = True) -> Optional[Dict]:
        """
        Extract URL data from <url> element.

        Args:
            url_elem: URL XML element
            with_ns: Whether to use namespace

        Returns:
            Dictionary with URL data or None
        """
        ns = self.SITEMAP_NS if with_ns else {}
        prefix = 'sm:' if with_ns else ''

        # Extract loc (required)
        loc_elem = url_elem.find(f'{prefix}loc', ns) if with_ns else url_elem.find('loc')
        if loc_elem is None or not loc_elem.text:
            return None

        url_data = {'loc': loc_elem.text.strip()}

        # Extract optional fields
        for field in ['lastmod', 'changefreq', 'priority']:
            elem = url_elem.find(f'{prefix}{field}', ns) if with_ns else url_elem.find(field)
            if elem is not None and elem.text:
                url_data[field] = elem.text.strip()

        return url_data

    def parse_sitemap_recursive(self, url: str, max_depth: int = 3, track_errors: bool = False) -> List[Dict]:
        """
        Parse sitemap recursively, following sitemap index references.

        Args:
            url: Sitemap URL (can be index or regular)
            max_depth: Maximum recursion depth
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
        Parse sitemap recursively with detailed error tracking.

        Args:
            url: Sitemap URL (can be index or regular)
            max_depth: Maximum recursion depth

        Returns:
            Dictionary with 'urls', 'errors', 'visited_sitemaps' keys

        Raises:
            ValueError: If max_urls limit is exceeded
        """
        all_urls = []
        visited_sitemaps = set()
        errors = []

        def _parse_recursive(sitemap_url: str, depth: int):
            if depth > max_depth:
                errors.append({
                    'url': sitemap_url,
                    'error': f'Exceeded max depth ({max_depth})',
                    'depth': depth
                })
                return

            if sitemap_url in visited_sitemaps:
                return

            visited_sitemaps.add(sitemap_url)

            # Fetch and parse
            try:
                print(f"[Sitemap] Fetching: {sitemap_url} (depth {depth})")
                content = self.fetch_sitemap(sitemap_url)
                result = self.parse_sitemap(content)

                # Add URLs
                if result.get('urls'):
                    all_urls.extend(result['urls'])
                    print(f"[Sitemap] Found {len(result['urls'])} URLs from {sitemap_url}")

                    # Check limit
                    if len(all_urls) > self.max_urls:
                        raise ValueError(f"Exceeded maximum URL limit ({self.max_urls})")

                # Recursively parse nested sitemaps
                if result.get('sitemaps'):
                    print(f"[Sitemap] Found {len(result['sitemaps'])} child sitemaps in {sitemap_url}")
                    for nested_url in result['sitemaps']:
                        # Resolve relative URLs to absolute URLs
                        absolute_nested_url = self.normalize_url(nested_url, base_url=sitemap_url)
                        _parse_recursive(absolute_nested_url, depth + 1)

            except Exception as e:
                error_msg = str(e)
                print(f"[Sitemap] Error parsing {sitemap_url}: {error_msg}")
                errors.append({
                    'url': sitemap_url,
                    'error': error_msg,
                    'depth': depth
                })

        _parse_recursive(url, 0)

        return {
            'urls': all_urls,
            'errors': errors,
            'visited_sitemaps': list(visited_sitemaps),
            'total_sitemaps': len(visited_sitemaps),
            'total_urls': len(all_urls),
            'has_errors': len(errors) > 0
        }

    def normalize_url(self, url: str, base_url: str = None) -> str:
        """
        Normalize URL (resolve relative URLs, remove fragments).

        Args:
            url: URL to normalize
            base_url: Base URL for resolving relative URLs

        Returns:
            Normalized URL
        """
        # Resolve relative URL
        if base_url:
            url = urljoin(base_url, url)

        # Parse and remove fragment
        parsed = urlparse(url)
        normalized = parsed._replace(fragment='').geturl()

        return normalized

    def extract_urls(self, content: str, base_url: str = None) -> List[str]:
        """
        Extract just the URLs from sitemap (convenience method).

        Args:
            content: Sitemap XML content
            base_url: Base URL for normalization

        Returns:
            List of URL strings
        """
        result = self.parse_sitemap(content)
        urls = []

        for url_data in result.get('urls', []):
            url = url_data.get('loc')
            if url:
                if base_url:
                    url = self.normalize_url(url, base_url)
                urls.append(url)

        return urls


# Global sitemap parser instance
sitemap_parser = SitemapParser(
    timeout=settings.page_timeout,
    max_urls=10000
)
