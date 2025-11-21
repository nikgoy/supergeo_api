"""
Gemini AI service for processing markdown and generating SEO-optimized HTML.

This service uses the Google GenAI SDK to:
1. Clean and optimize raw markdown content
2. Generate GEO (Generative Engine Optimization) HTML from markdown
3. Support batch processing with rate limiting

Uses client-specific API keys when available, falls back to global key.
"""
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple
from datetime import datetime
from uuid import UUID

from google import genai
from google.genai import errors as genai_errors
from sqlalchemy.orm import Session

from app.config import settings

# Avoid circular imports
if TYPE_CHECKING:
    from app.models.client import Client, Page


class GeminiService:
    """
    Service for interacting with Google Gemini API.

    Handles markdown processing and HTML generation for page content.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash-exp",
        timeout: int = 60
    ):
        """
        Initialize Gemini service.

        Args:
            api_key: Gemini API key (uses settings.gemini_api_key if not provided)
            model: Model to use for generation
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.gemini_api_key
        self.model = model
        self.timeout = timeout

        if not self.api_key:
            raise ValueError("Gemini API key is required")

    def _get_client(self) -> genai.Client:
        """
        Create a Gemini client instance.

        Returns:
            Configured Gemini client
        """
        return genai.Client(api_key=self.api_key)

    @classmethod
    def from_client(cls, client: "Client") -> "GeminiService":
        """
        Create service instance using client's API key.

        Args:
            client: Client model with gemini_api_key

        Returns:
            GeminiService configured with client's key

        Raises:
            ValueError: If client has no Gemini API key
        """
        api_key = client.gemini_api_key
        if not api_key:
            # Fall back to global key
            api_key = settings.gemini_api_key

        if not api_key:
            raise ValueError(
                f"No Gemini API key found for client {client.id} "
                "and no global fallback configured"
            )

        return cls(api_key=api_key)

    def get_markdown_cleaning_prompt(self, raw_markdown: str) -> str:
        """
        Generate prompt for cleaning raw markdown.

        Args:
            raw_markdown: Raw markdown content from scraper

        Returns:
            Prompt string
        """
        return f"""Clean and optimize the following markdown content for LLM consumption.

Requirements:
1. Remove navigation menus, footers, and boilerplate text
2. Keep only the main content (product info, descriptions, features)
3. Preserve important structure (headings, lists, pricing)
4. Remove redundant whitespace and formatting
5. Keep prices, specifications, and key details
6. Maintain a clear, concise structure

Return ONLY the cleaned markdown without any explanation or wrapper.

Raw Markdown:
---
{raw_markdown}
---"""

    def get_html_generation_prompt(
        self,
        markdown: str,
        url: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Generate prompt for creating SEO-optimized HTML.

        Args:
            markdown: Cleaned markdown content
            url: Page URL
            metadata: Optional metadata (title, description, etc.)

        Returns:
            Prompt string
        """
        metadata = metadata or {}
        title = metadata.get("title", "Page")
        description = metadata.get("description", "")

        return f"""Generate SEO-optimized, semantic HTML from the following markdown content.

URL: {url}
Title: {title}
Description: {description}

Requirements:
1. Create valid HTML5 with proper semantic tags
2. Include comprehensive meta tags (description, viewport, robots)
3. Add Schema.org structured data (use itemscope, itemtype, itemprop)
4. Use semantic HTML: <article>, <section>, <header>, <h1-h6>
5. Make it optimized for AI search engines (GEO - Generative Engine Optimization)
6. Include pricing schema if product information is present
7. Add proper microdata for better search visibility
8. Keep it clean and readable

Return ONLY the complete HTML document without markdown code blocks or explanations.

Markdown Content:
---
{markdown}
---"""

    def process_markdown(self, raw_markdown: str) -> str:
        """
        Clean and optimize raw markdown content.

        Args:
            raw_markdown: Raw markdown from scraper

        Returns:
            Cleaned markdown optimized for LLMs

        Raises:
            Exception: If Gemini API fails
        """
        if not raw_markdown or not raw_markdown.strip():
            raise ValueError("Raw markdown cannot be empty")

        prompt = self.get_markdown_cleaning_prompt(raw_markdown)

        try:
            with self._get_client() as client:
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt
                )

                if not response.text:
                    raise Exception("Gemini returned empty response for markdown processing")

                return response.text.strip()

        except genai_errors.APIError as e:
            raise Exception(f"Gemini API error: {e.code} - {e.message}")
        except Exception as e:
            raise Exception(f"Failed to process markdown: {str(e)}")

    def generate_html(
        self,
        markdown: str,
        url: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Generate SEO-optimized HTML from markdown.

        Args:
            markdown: Cleaned markdown content
            url: Page URL for context
            metadata: Optional page metadata

        Returns:
            SEO-optimized HTML

        Raises:
            Exception: If Gemini API fails
        """
        if not markdown or not markdown.strip():
            raise ValueError("Markdown cannot be empty")

        prompt = self.get_html_generation_prompt(markdown, url, metadata)

        try:
            with self._get_client() as client:
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt
                )

                if not response.text:
                    raise Exception("Gemini returned empty response for HTML generation")

                html = response.text.strip()

                # Remove markdown code blocks if present
                if html.startswith("```html"):
                    html = html[7:]
                if html.startswith("```"):
                    html = html[3:]
                if html.endswith("```"):
                    html = html[:-3]

                return html.strip()

        except genai_errors.APIError as e:
            raise Exception(f"Gemini API error: {e.code} - {e.message}")
        except Exception as e:
            raise Exception(f"Failed to generate HTML: {str(e)}")

    def process_page(
        self,
        db: Session,
        page_id: UUID
    ) -> Dict:
        """
        Process a single page: clean markdown and generate HTML.

        Args:
            db: Database session
            page_id: Page UUID

        Returns:
            Dict with processing results

        Raises:
            ValueError: If page not found or missing required data
            Exception: If processing fails
        """
        # Import here to avoid circular import
        from app.models.client import Page

        # Get page
        page = db.query(Page).filter(Page.id == page_id).first()
        if not page:
            raise ValueError(f"Page {page_id} not found")

        # Check if page has raw markdown
        if not page.raw_markdown:
            raise ValueError(f"Page {page_id} has no raw_markdown to process")

        # Process markdown
        print(f"Processing markdown for page {page_id}...")
        llm_markdown = self.process_markdown(page.raw_markdown)

        # Generate HTML
        print(f"Generating HTML for page {page_id}...")
        metadata = {"title": page.url.split("/")[-1].replace("-", " ").title()}
        geo_html = self.generate_html(llm_markdown, page.url, metadata)

        # Update page
        page.llm_markdown = llm_markdown
        page.geo_html = geo_html
        page.last_processed_at = datetime.utcnow()

        db.commit()
        db.refresh(page)

        return {
            "page_id": str(page.id),
            "url": page.url,
            "llm_markdown_length": len(llm_markdown),
            "geo_html_length": len(geo_html),
            "processed_at": page.last_processed_at.isoformat()
        }

    def process_client_pages(
        self,
        db: Session,
        client_id: UUID,
        force: bool = False,
        batch_size: int = 10
    ) -> Dict:
        """
        Process all pages for a client.

        Args:
            db: Database session
            client_id: Client UUID
            force: Reprocess already-processed pages
            batch_size: Number of pages to process at once

        Returns:
            Dict with processing statistics

        Raises:
            ValueError: If client not found
        """
        # Import here to avoid circular import
        from app.models.client import Client, Page

        # Verify client exists
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise ValueError(f"Client {client_id} not found")

        # Get pages to process
        query = db.query(Page).filter(
            Page.client_id == client_id,
            Page.raw_markdown.isnot(None)
        )

        # Skip already processed unless force=True
        if not force:
            query = query.filter(Page.geo_html.is_(None))

        pages = query.limit(batch_size).all()

        # TODO: Implement rate limiting to respect Gemini API quotas
        # Consider using exponential backoff and request batching

        processed = 0
        skipped = 0
        failed = 0
        errors = []

        for page in pages:
            try:
                # Skip if already processed and not forcing
                if not force and page.geo_html is not None:
                    skipped += 1
                    continue

                print(f"Processing page {page.id} ({page.url})...")

                # Process markdown
                llm_markdown = self.process_markdown(page.raw_markdown)

                # Generate HTML
                metadata = {"title": page.url.split("/")[-1].replace("-", " ").title()}
                geo_html = self.generate_html(llm_markdown, page.url, metadata)

                # Update page
                page.llm_markdown = llm_markdown
                page.geo_html = geo_html
                page.last_processed_at = datetime.utcnow()

                db.commit()
                processed += 1

            except Exception as e:
                failed += 1
                error_msg = f"Page {page.id}: {str(e)}"
                errors.append(error_msg)
                print(f"Error: {error_msg}")
                db.rollback()

        return {
            "client_id": str(client_id),
            "processed": processed,
            "skipped": skipped,
            "failed": failed,
            "errors": errors,
            "total_pages": len(pages)
        }


# Global service instance using default settings
gemini_service = GeminiService()
