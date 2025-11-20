"""
Apify RAG Web Browser integration service.

Provides scraping functionality using Apify's rag-web-browser actor to extract
raw markdown content from URLs. Supports both single URL and batch processing
with parallel execution.
"""
import time
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from apify_client import ApifyClient

from app.config import settings


class ApifyRagService:
    """Service for integrating with Apify RAG Web Browser actor."""

    # Apify actor ID for rag-web-browser
    ACTOR_ID = "apify/rag-web-browser"

    def __init__(
        self,
        api_token: Optional[str] = None,
        timeout: int = 120,
        max_parallel: int = 5,
        max_retries: int = 3
    ):
        """
        Initialize Apify RAG service.

        Args:
            api_token: Apify API token (defaults to settings.apify_api_token)
            timeout: Timeout for scraping in seconds
            max_parallel: Maximum parallel requests
            max_retries: Maximum retry attempts for failed scrapes
        """
        self.api_token = api_token or settings.apify_api_token
        self.timeout = timeout
        self.max_parallel = max_parallel
        self.max_retries = max_retries
        self.client = ApifyClient(self.api_token)

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
            wait_for_completion: If True, wait for actor run to complete
            retry_count: Current retry attempt (used internally)

        Returns:
            Dictionary containing:
                - status: 'success' | 'failed' | 'timeout' | 'pending'
                - markdown: Raw markdown content (if success)
                - run_id: Apify actor run ID
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
            # Prepare actor input
            actor_input = {
                "startUrls": [{"url": url}],
                "maxCrawlDepth": 0,  # Single page only
                "crawlerType": "playwright:chrome",  # Use headless browser
                "includeMarkdown": True,
                "removeCookieWarnings": True,
                "removeCollapsibleElements": True,
            }

            # Run the actor
            run = self.client.actor(self.ACTOR_ID).call(
                run_input=actor_input,
                timeout_secs=self.timeout,
                wait_secs=self.timeout if wait_for_completion else 0
            )

            run_id = run.get("id")
            status = run.get("status")

            print(f"[Apify] Run {run_id} status: {status}")

            # If not waiting, return pending status
            if not wait_for_completion:
                return {
                    "status": "pending",
                    "run_id": run_id,
                    "url": url,
                    "metadata": {
                        "apify_status": status,
                        "started_at": run.get("startedAt"),
                    }
                }

            # Check if run succeeded
            if status != "SUCCEEDED":
                error_msg = f"Actor run failed with status: {status}"
                print(f"[Apify] Error: {error_msg}")

                # Retry logic
                if retry_count < self.max_retries - 1:
                    print(f"[Apify] Retrying in 2 seconds...")
                    time.sleep(2)
                    return self.scrape_url(url, wait_for_completion, retry_count + 1)

                return {
                    "status": "failed",
                    "run_id": run_id,
                    "url": url,
                    "error": error_msg,
                    "metadata": {
                        "apify_status": status,
                        "finished_at": run.get("finishedAt"),
                    }
                }

            # Fetch results from dataset
            dataset_id = run.get("defaultDatasetId")
            if not dataset_id:
                error_msg = "No dataset ID returned from Apify"
                print(f"[Apify] Error: {error_msg}")
                return {
                    "status": "failed",
                    "run_id": run_id,
                    "url": url,
                    "error": error_msg,
                }

            # Get dataset items
            dataset_client = self.client.dataset(dataset_id)
            items = list(dataset_client.iterate_items())

            if not items:
                error_msg = "No items returned from Apify dataset"
                print(f"[Apify] Error: {error_msg}")
                return {
                    "status": "failed",
                    "run_id": run_id,
                    "url": url,
                    "error": error_msg,
                }

            # Extract markdown from first item
            first_item = items[0]
            markdown = first_item.get("markdown", "")

            if not markdown:
                # Try text field as fallback
                markdown = first_item.get("text", "")

            if not markdown:
                error_msg = "No markdown content found in Apify results"
                print(f"[Apify] Warning: {error_msg}")
                # Don't fail, return empty markdown
                markdown = ""

            print(f"[Apify] Successfully scraped {len(markdown)} characters from {url}")

            return {
                "status": "success",
                "markdown": markdown,
                "run_id": run_id,
                "url": url,
                "metadata": {
                    "apify_status": status,
                    "finished_at": run.get("finishedAt"),
                    "markdown_length": len(markdown),
                    "crawled_url": first_item.get("url", url),
                    "title": first_item.get("title"),
                    "language": first_item.get("language"),
                }
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
                "run_id": None,
                "url": url,
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
                        "run_id": None,
                        "url": url,
                        "error": f"Exception during parallel execution: {str(e)}",
                    })

        print(f"[Apify] Parallel scraping completed: {len(results)} results")
        return results

    def get_run_status(self, run_id: str) -> Dict:
        """
        Get status of a specific Apify actor run.

        Args:
            run_id: Apify actor run ID

        Returns:
            Dictionary containing run status information

        Example:
            >>> service = ApifyRagService()
            >>> status = service.get_run_status("abc123")
            >>> print(status['status'])
        """
        try:
            run = self.client.run(run_id).get()

            return {
                "run_id": run_id,
                "status": run.get("status"),
                "started_at": run.get("startedAt"),
                "finished_at": run.get("finishedAt"),
                "build_number": run.get("buildNumber"),
                "exit_code": run.get("exitCode"),
                "default_dataset_id": run.get("defaultDatasetId"),
            }
        except Exception as e:
            return {
                "run_id": run_id,
                "status": "error",
                "error": f"Failed to get run status: {str(e)}",
            }


# Global singleton instance
apify_rag_service = ApifyRagService(
    timeout=settings.apify_timeout,
    max_parallel=settings.apify_max_parallel,
    max_retries=settings.apify_max_retries
)
