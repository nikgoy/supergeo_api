"""
Referrer Analytics and Attribution Service.

Provides AI source detection, conversion attribution, and revenue analytics
for understanding ROI from AI bot traffic.
"""
from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from urllib.parse import urlparse
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.models.base import SessionLocal
from app.models.client import Client, Page, Visit, Order


# AI referrer domain patterns
AI_REFERRER_PATTERNS = {
    'ChatGPT': ['chat.openai.com', 'chatgpt.com', 'openai.com/chat'],
    'Perplexity': ['perplexity.ai', 'www.perplexity.ai'],
    'Claude': ['claude.ai', 'anthropic.com/claude'],
    'Gemini': ['gemini.google.com', 'bard.google.com'],
    'Bing': ['bing.com/chat', 'bing.com/search'],
    'Google': ['google.com/search', 'google.com'],
}


def detect_ai_source_from_referrer(referrer: Optional[str]) -> Optional[str]:
    """
    Detect AI source from referrer URL.

    Args:
        referrer: Full referrer URL

    Returns:
        AI source name (e.g., 'ChatGPT', 'Perplexity') or None
    """
    if not referrer:
        return None

    referrer_lower = referrer.lower()

    # Try to parse the domain
    try:
        parsed = urlparse(referrer_lower)
        domain = parsed.netloc or parsed.path
    except Exception:
        domain = referrer_lower

    # Check against known AI patterns
    for ai_source, patterns in AI_REFERRER_PATTERNS.items():
        for pattern in patterns:
            if pattern in domain or pattern in referrer_lower:
                return ai_source

    return None


def extract_referrer_domain(referrer: Optional[str]) -> Optional[str]:
    """
    Extract domain from referrer URL.

    Args:
        referrer: Full referrer URL

    Returns:
        Domain string or None
    """
    if not referrer:
        return None

    try:
        parsed = urlparse(referrer)
        return parsed.netloc or None
    except Exception:
        return None


def get_conversion_analytics(
    client_id: UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict:
    """
    Get conversion analytics for a client.

    Args:
        client_id: Client UUID
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        Dictionary with conversion analytics
    """
    db = SessionLocal()
    try:
        # Build base query
        query = db.query(Order).filter(Order.client_id == client_id)

        # Apply date filters if provided
        if start_date:
            query = query.filter(Order.converted_at >= start_date)
        if end_date:
            query = query.filter(Order.converted_at <= end_date)

        # Total conversions
        total_conversions = query.count()

        # Total revenue
        total_revenue = query.with_entities(
            func.sum(Order.conversion_value)
        ).scalar() or 0.0

        # AI conversions (with ai_source)
        ai_conversions = query.filter(Order.ai_source.isnot(None)).count()

        # AI revenue
        ai_revenue = query.filter(
            Order.ai_source.isnot(None)
        ).with_entities(
            func.sum(Order.conversion_value)
        ).scalar() or 0.0

        # Calculate percentages
        ai_conversion_rate = (ai_conversions / total_conversions * 100) if total_conversions > 0 else 0
        ai_revenue_rate = (ai_revenue / total_revenue * 100) if total_revenue > 0 else 0

        return {
            'total_conversions': total_conversions,
            'total_revenue': round(total_revenue, 2),
            'ai_conversions': ai_conversions,
            'ai_revenue': round(ai_revenue, 2),
            'ai_conversion_rate': round(ai_conversion_rate, 2),
            'ai_revenue_rate': round(ai_revenue_rate, 2),
            'start_date': start_date.isoformat() if start_date else None,
            'end_date': end_date.isoformat() if end_date else None
        }

    finally:
        db.close()


def get_conversions_by_ai_source(
    client_id: UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict]:
    """
    Get conversions grouped by AI source.

    Args:
        client_id: Client UUID
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        List of dictionaries with AI source breakdowns
    """
    db = SessionLocal()
    try:
        # Build base query
        query = db.query(
            Order.ai_source,
            func.count(Order.id).label('conversion_count'),
            func.sum(Order.conversion_value).label('total_revenue')
        ).filter(
            Order.client_id == client_id,
            Order.ai_source.isnot(None)
        )

        # Apply date filters
        if start_date:
            query = query.filter(Order.converted_at >= start_date)
        if end_date:
            query = query.filter(Order.converted_at <= end_date)

        # Group and order
        results = query.group_by(
            Order.ai_source
        ).order_by(
            desc('total_revenue')
        ).all()

        return [
            {
                'ai_source': ai_source,
                'conversion_count': conversion_count,
                'total_revenue': round(total_revenue or 0, 2),
                'avg_order_value': round((total_revenue or 0) / conversion_count, 2) if conversion_count > 0 else 0
            }
            for ai_source, conversion_count, total_revenue in results
        ]

    finally:
        db.close()


def get_top_converting_pages(
    client_id: UUID,
    limit: int = 10,
    days: int = 30
) -> List[Dict]:
    """
    Get top converting pages.

    Args:
        client_id: Client UUID
        limit: Maximum number of results
        days: Number of days to look back

    Returns:
        List of dictionaries with page conversion data
    """
    db = SessionLocal()
    try:
        start_date = datetime.utcnow() - timedelta(days=days)

        results = db.query(
            Order.landing_url,
            Order.page_id,
            func.count(Order.id).label('conversion_count'),
            func.sum(Order.conversion_value).label('total_revenue')
        ).filter(
            Order.client_id == client_id,
            Order.converted_at >= start_date
        ).group_by(
            Order.landing_url,
            Order.page_id
        ).order_by(
            desc('conversion_count')
        ).limit(limit).all()

        return [
            {
                'landing_url': landing_url,
                'page_id': str(page_id) if page_id else None,
                'conversion_count': conversion_count,
                'total_revenue': round(total_revenue or 0, 2)
            }
            for landing_url, page_id, conversion_count, total_revenue in results
        ]

    finally:
        db.close()


def get_conversions_time_series(
    client_id: UUID,
    start_date: datetime,
    end_date: datetime,
    interval: str = 'day'
) -> List[Dict]:
    """
    Get conversions time series data.

    Args:
        client_id: Client UUID
        start_date: Start date for time series
        end_date: End date for time series
        interval: Interval ('hour', 'day', 'week')

    Returns:
        List of dictionaries with time series data
    """
    db = SessionLocal()
    try:
        # Determine date truncation based on interval
        if interval == 'hour':
            date_trunc = func.date_trunc('hour', Order.converted_at)
        elif interval == 'week':
            date_trunc = func.date_trunc('week', Order.converted_at)
        else:  # default to day
            date_trunc = func.date_trunc('day', Order.converted_at)

        # Query conversions
        results = db.query(
            date_trunc.label('date'),
            func.count(Order.id).label('conversion_count'),
            func.sum(Order.conversion_value).label('revenue')
        ).filter(
            Order.client_id == client_id,
            Order.converted_at >= start_date,
            Order.converted_at <= end_date
        ).group_by(
            date_trunc
        ).order_by(
            date_trunc
        ).all()

        return [
            {
                'date': date.isoformat() if date else None,
                'conversion_count': conversion_count,
                'revenue': round(revenue or 0, 2)
            }
            for date, conversion_count, revenue in results
        ]

    finally:
        db.close()


def get_referrer_analytics_dashboard(
    client_id: UUID,
    days: int = 30
) -> Dict:
    """
    Get comprehensive referrer analytics dashboard data.

    Args:
        client_id: Client UUID
        days: Number of days to analyze

    Returns:
        Dictionary with comprehensive analytics
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    end_date = datetime.utcnow()

    # Get conversion analytics
    analytics = get_conversion_analytics(client_id, start_date, end_date)

    # Get AI source breakdown
    by_ai_source = get_conversions_by_ai_source(client_id, start_date, end_date)

    # Get top converting pages
    top_pages = get_top_converting_pages(client_id, limit=10, days=days)

    # Get time series
    time_series = get_conversions_time_series(
        client_id,
        start_date,
        end_date,
        interval='day'
    )

    return {
        'summary': analytics,
        'by_ai_source': by_ai_source,
        'top_converting_pages': top_pages,
        'time_series': time_series,
        'period_days': days
    }


# TODO: Attribution models (first-touch, last-touch, multi-touch)
# These would require tracking visit sessions and linking to conversions
def attribute_conversion(
    visits: List[Dict],
    model: str = 'last_touch'
) -> Dict:
    """
    Attribute conversion to traffic source.

    NOTE: This is a placeholder for future attribution logic.
    Would require session tracking and visit-to-conversion linking.

    Args:
        visits: List of visit dictionaries with referrer and timestamp
        model: Attribution model ('first_touch', 'last_touch', 'multi_touch')

    Returns:
        Dictionary with attribution results
    """
    # TODO: Implement attribution models
    # For now, return simple last-touch attribution
    if not visits:
        return {'source': None, 'model': model}

    if model == 'first_touch':
        # Attribute to first visit
        first_visit = visits[0]
        ai_source = detect_ai_source_from_referrer(first_visit.get('referrer'))
        return {'source': ai_source, 'model': 'first_touch'}

    elif model == 'last_touch':
        # Attribute to last visit
        last_visit = visits[-1]
        ai_source = detect_ai_source_from_referrer(last_visit.get('referrer'))
        return {'source': ai_source, 'model': 'last_touch'}

    elif model == 'multi_touch':
        # TODO: Implement multi-touch attribution
        # Would split credit among multiple touchpoints
        sources = []
        for visit in visits:
            ai_source = detect_ai_source_from_referrer(visit.get('referrer'))
            if ai_source and ai_source not in sources:
                sources.append(ai_source)

        return {'sources': sources, 'model': 'multi_touch'}

    return {'source': None, 'model': model}
