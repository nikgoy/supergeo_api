"""
Service for calculating page analytics.

This service computes aggregated metrics about pages for each client,
tracking progress through the processing pipeline.
"""
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.client import Page, PageAnalytics, Client


class PageAnalyticsService:
    """Service for calculating and managing page analytics."""

    @staticmethod
    def calculate_analytics(db: Session, client_id: UUID) -> PageAnalytics:
        """
        Calculate analytics for a specific client.

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            PageAnalytics object with calculated metrics

        Raises:
            ValueError: If client doesn't exist
        """
        # Verify client exists
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise ValueError(f"Client with id {client_id} not found")

        # Calculate total URLs
        total_urls = db.query(func.count(Page.id)).filter(
            Page.client_id == client_id
        ).scalar() or 0

        # Calculate URLs with raw markdown
        urls_with_raw_markdown = db.query(func.count(Page.id)).filter(
            Page.client_id == client_id,
            Page.raw_markdown.isnot(None),
            Page.raw_markdown != ''
        ).scalar() or 0

        # Calculate URLs with LLM markdown
        urls_with_markdown = db.query(func.count(Page.id)).filter(
            Page.client_id == client_id,
            Page.llm_markdown.isnot(None),
            Page.llm_markdown != ''
        ).scalar() or 0

        # Calculate URLs with geo HTML
        urls_with_geo_html = db.query(func.count(Page.id)).filter(
            Page.client_id == client_id,
            Page.geo_html.isnot(None),
            Page.geo_html != ''
        ).scalar() or 0

        # Calculate URLs with KV key
        urls_with_kv_key = db.query(func.count(Page.id)).filter(
            Page.client_id == client_id,
            Page.kv_key.isnot(None),
            Page.kv_key != ''
        ).scalar() or 0

        # Calculate completion rates
        html_completion_rate = (urls_with_raw_markdown / total_urls * 100) if total_urls > 0 else 0.0
        markdown_completion_rate = (urls_with_markdown / total_urls * 100) if total_urls > 0 else 0.0
        geo_html_completion_rate = (urls_with_geo_html / total_urls * 100) if total_urls > 0 else 0.0
        kv_upload_completion_rate = (urls_with_kv_key / total_urls * 100) if total_urls > 0 else 0.0

        # Calculate pages updated in last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        pages_updated_last_30_days = db.query(func.count(Page.id)).filter(
            Page.client_id == client_id,
            Page.updated_at >= thirty_days_ago
        ).scalar() or 0

        # Check if analytics record exists
        analytics = db.query(PageAnalytics).filter(
            PageAnalytics.client_id == client_id
        ).first()

        if analytics:
            # Update existing record
            analytics.total_urls = total_urls
            analytics.urls_with_raw_markdown = urls_with_raw_markdown
            analytics.urls_with_markdown = urls_with_markdown
            analytics.urls_with_geo_html = urls_with_geo_html
            analytics.urls_with_kv_key = urls_with_kv_key
            analytics.html_completion_rate = html_completion_rate
            analytics.markdown_completion_rate = markdown_completion_rate
            analytics.geo_html_completion_rate = geo_html_completion_rate
            analytics.kv_upload_completion_rate = kv_upload_completion_rate
            analytics.pages_updated_last_30_days = pages_updated_last_30_days
            analytics.last_calculated_at = datetime.utcnow()
        else:
            # Create new record
            analytics = PageAnalytics(
                client_id=client_id,
                total_urls=total_urls,
                urls_with_raw_markdown=urls_with_raw_markdown,
                urls_with_markdown=urls_with_markdown,
                urls_with_geo_html=urls_with_geo_html,
                urls_with_kv_key=urls_with_kv_key,
                html_completion_rate=html_completion_rate,
                markdown_completion_rate=markdown_completion_rate,
                geo_html_completion_rate=geo_html_completion_rate,
                kv_upload_completion_rate=kv_upload_completion_rate,
                pages_updated_last_30_days=pages_updated_last_30_days,
                last_calculated_at=datetime.utcnow()
            )
            db.add(analytics)

        db.commit()
        db.refresh(analytics)
        return analytics

    @staticmethod
    def calculate_all_analytics(db: Session) -> List[PageAnalytics]:
        """
        Calculate analytics for all clients.

        Args:
            db: Database session

        Returns:
            List of PageAnalytics objects
        """
        # Get all active clients
        clients = db.query(Client).filter(Client.is_active == True).all()

        analytics_list = []
        for client in clients:
            try:
                analytics = PageAnalyticsService.calculate_analytics(db, client.id)
                analytics_list.append(analytics)
            except Exception as e:
                # Log error but continue with other clients
                print(f"Error calculating analytics for client {client.id}: {e}")
                continue

        return analytics_list

    @staticmethod
    def get_analytics(db: Session, client_id: UUID) -> Optional[PageAnalytics]:
        """
        Get analytics for a specific client without recalculating.

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            PageAnalytics object or None if not found
        """
        return db.query(PageAnalytics).filter(
            PageAnalytics.client_id == client_id
        ).first()

    @staticmethod
    def get_all_analytics(
        db: Session,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[PageAnalytics], int]:
        """
        Get analytics for all clients with pagination.

        Args:
            db: Database session
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            Tuple of (analytics list, total count)
        """
        query = db.query(PageAnalytics)
        total = query.count()

        analytics = query.order_by(
            PageAnalytics.last_calculated_at.desc()
        ).limit(limit).offset(offset).all()

        return analytics, total


# Singleton instance
page_analytics_service = PageAnalyticsService()
