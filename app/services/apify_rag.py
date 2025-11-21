"""
Apify RAG Web Browser integration service.

Provides scraping functionality using Apify's rag-web-browser actor to extract
raw markdown content from URLs. Supports both single URL and batch processing
with parallel execution.
"""
import time
import requests
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from app.config import settings


class ApifyRagService:
    """Service for integrating with Apify RAG Web Browser actor."""

    # Apify API endpoint for rag-web-browser
    API_ENDPOINT = "https://rag-web-browser.apify.actor"

    def __init__(
        self,
        api_token: Optional[str] = None,
        timeout: int = 120,
        max_parallel: int = 10,
        max_retries: int = 3
    ):
        """
        Initialize Apify RAG service.

        Args:
            api_token: Apify API token (defaults to settings.apify_api_token)
            timeout: Timeout for scraping in seconds
            max_parallel: Maximum parallel requests (default: 10)
            max_retries: Maximum retry attempts for failed scrapes
        """
        self.api_token = api_token or settings.apify_api_token
        self.timeout = timeout
        self.max_parallel = max_parallel
        self.max_retries = max_retries

    def scrape_url(
        self,
        url: str,
        wait_for_completion: bool = True,
        retry_count: int = 0
    ) -> Dict:
        """
        Scrape a single URL using Apify RAG Web Browser.

        Args:
            url: URL to scrape
            wait_for_completion: If True, wait for actor run to complete (unused, kept for compatibility)
            retry_count: Current retry attempt (used internally)

        Returns:
            Dictionary containing:
                - status: 'success' | 'failed'
                - markdown: Raw markdown content (if success)
                - url: Original URL
                - error: Error message (if failed)
                - metadata: Additional metadata from Apify

        Example:
            >>> service = ApifyRagService()
            >>> result = service.scrape_url("https://example.com")
            >>> print(result['markdown'])
        """
        print(f"[Apify] Scraping URL: {url} (attempt {retry_count + 1}/{self.max_retries})")

        try:
            # Prepare request payload
            payload = {
                "debugMode": False,
                "desiredConcurrency": 5,
                "htmlTransformer": "none",
                "maxResults": 1,
                "outputFormats": ["markdown"],
                "proxyConfiguration": {
                    "useApifyProxy": True
                },
                "query": url,
                "removeCookieWarnings": True,
                "removeElementsCssSelector": (
                    "nav, footer, script, style, noscript, svg, img[src^='data:'],\n"
                    "[role=\"alert\"],\n"
                    "[role=\"banner\"],\n"
                    "[role=\"dialog\"],\n"
                    "[role=\"alertdialog\"],\n"
                    "[role=\"region\"][aria-label*=\"skip\" i],\n"
                    "[aria-modal=\"true\"]"
                ),
                "requestTimeoutSecs": 40
            }

            # Make POST request to Apify API
            api_url = f"{self.API_ENDPOINT}?token={self.api_token}"

            print(f"[Apify] Sending POST request to {self.API_ENDPOINT}")
            response = requests.post(
                api_url,
                json=payload,
                timeout=self.timeout
            )

            # Check response status
            if response.status_code != 200:
                error_msg = f"Apify API returned status {response.status_code}: {response.text}"
                print(f"[Apify] Error: {error_msg}")

                # Retry logic
                if retry_count < self.max_retries - 1:
                    print(f"[Apify] Retrying in 2 seconds...")
                    time.sleep(2)
                    return self.scrape_url(url, wait_for_completion, retry_count + 1)

                return {
                    "status": "failed",
                    "url": url,
                    "run_id": None,
                    "error": error_msg,
                }

            # Parse response
            results = response.json()

            if not isinstance(results, list) or not results:
                error_msg = "No results returned from Apify API"
                print(f"[Apify] Error: {error_msg}")

                # Retry logic
                if retry_count < self.max_retries - 1:
                    print(f"[Apify] Retrying in 2 seconds...")
                    time.sleep(2)
                    return self.scrape_url(url, wait_for_completion, retry_count + 1)

                return {
                    "status": "failed",
                    "url": url,
                    "run_id": None,
                    "error": error_msg,
                }

            # Extract first result
            first_result = results[0]
            markdown = first_result.get("markdown", "")

            if not markdown:
                # Try text field as fallback
                markdown = first_result.get("text", "")

            if not markdown:
                error_msg = "No markdown content found in Apify results"
                print(f"[Apify] Warning: {error_msg}")
                # Don't fail, return empty markdown
                markdown = ""

            result_url = first_result.get("url", url)

            print(f"[Apify] Successfully scraped {len(markdown)} characters from {url}")

            return {
                "status": "success",
                "markdown": markdown,
                "url": url,
                "run_id": None,  # No run ID with direct API calls
                "metadata": {
                    "markdown_length": len(markdown),
                    "crawled_url": result_url,
                }
            }

        except requests.exceptions.Timeout:
            error_msg = f"Request timeout after {self.timeout} seconds"
            print(f"[Apify] Error: {error_msg}")

            # Retry logic for timeout
            if retry_count < self.max_retries - 1:
                print(f"[Apify] Retrying in 2 seconds...")
                time.sleep(2)
                return self.scrape_url(url, wait_for_completion, retry_count + 1)

            return {
                "status": "failed",
                "url": url,
                "run_id": None,
                "error": error_msg,
            }

        except Exception as e:
            error_msg = f"Apify scraping error: {str(e)}"
            print(f"[Apify] Error: {error_msg}")

            # Retry logic for exceptions
            if retry_count < self.max_retries - 1:
                print(f"[Apify] Retrying in 2 seconds...")
                time.sleep(2)
                return self.scrape_url(url, wait_for_completion, retry_count + 1)

            return {
                "status": "failed",
                "url": url,
                "run_id": None,
                "error": error_msg,
            }

    def scrape_urls_parallel(
        self,
        urls: List[str],
        max_workers: Optional[int] = None
    ) -> List[Dict]:
        """
        Scrape multiple URLs in parallel.

        Args:
            urls: List of URLs to scrape
            max_workers: Maximum parallel workers (defaults to self.max_parallel)

        Returns:
            List of result dictionaries (same format as scrape_url)

        Example:
            >>> service = ApifyRagService()
            >>> urls = ["https://example.com", "https://test.com"]
            >>> results = service.scrape_urls_parallel(urls)
            >>> for result in results:
            ...     print(f"{result['url']}: {result['status']}")
        """
        max_workers = max_workers or self.max_parallel
        results = []

        print(f"[Apify] Starting parallel scrape of {len(urls)} URLs with {max_workers} workers")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_url = {
                executor.submit(self.scrape_url, url): url
                for url in urls
            }

            # Collect results as they complete
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results.append(result)
                    print(f"[Apify] Completed {len(results)}/{len(urls)}: {url}")
                except Exception as e:
                    print(f"[Apify] Exception for {url}: {str(e)}")
                    results.append({
                        "status": "failed",
                        "url": url,
                        "run_id": None,
                        "error": f"Exception during parallel execution: {str(e)}",
                    })

        print(f"[Apify] Parallel scraping completed: {len(results)} results")
        return results

    def get_run_status(self, run_id: str) -> Dict:
        """
        Get status of a specific Apify actor run.

        Note: This method is deprecated as the new API doesn't use run IDs.
        Kept for backward compatibility.

        Args:
            run_id: Apify actor run ID (deprecated)

        Returns:
            Dictionary containing run status information

        Example:
            >>> service = ApifyRagService()
            >>> status = service.get_run_status("abc123")
            >>> print(status['status'])
        """
        return {
            "run_id": run_id,
            "status": "not_supported",
            "error": "Run status tracking is not supported with the new direct API implementation",
        }


# Global singleton instance
apify_rag_service = ApifyRagService(
    timeout=settings.apify_timeout,
    max_parallel=settings.apify_max_parallel,
    max_retries=settings.apify_max_retries
)
