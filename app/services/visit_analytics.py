"""
Visit analytics service.

Provides analytics and aggregation for visit tracking data.
Separates bot crawl analytics from AI referral analytics.
Supports time series, top bots, top AI sources, and dashboard metrics.
"""
from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.models.base import SessionLocal
from app.models.client import Visit, Page


# Known AI bot patterns for auto-detection (crawler bots)
AI_BOT_PATTERNS = [
    'GPTBot',
    'PerplexityBot',
    'ClaudeBot',
    'anthropic-ai',
    'Googlebot',
    'Google-Extended',
    'Bingbot',
    'BingPreview',
    'FacebookBot',
    'Slackbot',
    'TwitterBot',
    'LinkedInBot',
    'WhatsApp',
    'facebookexternalhit',
]


def detect_bot_from_user_agent(user_agent: str) -> Optional[str]:
    """
    Detect bot crawler name from user agent string.

    Args:
        user_agent: User agent string

    Returns:
        Bot name if detected, None otherwise
    """
    if not user_agent:
        return None

    user_agent_lower = user_agent.lower()

    # Check for known patterns
    for pattern in AI_BOT_PATTERNS:
        if pattern.lower() in user_agent_lower:
            return pattern

    return None


def determine_visitor_type(user_agent: str, bot_name: Optional[str] = None, ai_source: Optional[str] = None) -> str:
    """
    Determine visitor type from user agent, bot name, and AI source.

    Args:
        user_agent: User agent string
        bot_name: Explicitly provided bot name (crawler)
        ai_source: AI chat app source (from referrer)

    Returns:
        'ai_bot', 'ai_referral', 'direct', or 'worker_proxy'
    """
    # Bot crawler detected
    if bot_name:
        return 'ai_bot'

    # Auto-detect bot from user agent
    detected_bot = detect_bot_from_user_agent(user_agent)
    if detected_bot:
        return 'ai_bot'

    # AI chat app referrer detected
    if ai_source:
        return 'ai_referral'

    return 'direct'


def get_top_bot_crawlers(client_id: UUID, limit: int = 10, days: int = 30) -> List[Dict]:
    """
    Get top bot crawlers by crawl count.

    Args:
        client_id: Client UUID
        limit: Maximum number of results
        days: Number of days to look back

    Returns:
        List of dictionaries with bot_name and crawl_count
    """
    db = SessionLocal()
    try:
        start_date = datetime.utcnow() - timedelta(days=days)

        results = db.query(
            Visit.bot_name,
            func.count(Visit.id).label('count')
        ).filter(
            Visit.client_id == client_id,
            Visit.visitor_type == 'ai_bot',
            Visit.bot_name.isnot(None),
            Visit.visited_at >= start_date
        ).group_by(
            Visit.bot_name
        ).order_by(
            desc('count')
        ).limit(limit).all()

        return [
            {
                'bot_name': bot_name,
                'crawl_count': count
            }
            for bot_name, count in results
        ]

    finally:
        db.close()


def get_top_ai_sources(client_id: UUID, limit: int = 10, days: int = 30) -> List[Dict]:
    """
    Get top AI chat app sources by visit count.

    Args:
        client_id: Client UUID
        limit: Maximum number of results
        days: Number of days to look back

    Returns:
        List of dictionaries with ai_source and visit_count
    """
    db = SessionLocal()
    try:
        start_date = datetime.utcnow() - timedelta(days=days)

        results = db.query(
            Visit.ai_source,
            func.count(Visit.id).label('count')
        ).filter(
            Visit.client_id == client_id,
            Visit.visitor_type == 'ai_referral',
            Visit.ai_source.isnot(None),
            Visit.visited_at >= start_date
        ).group_by(
            Visit.ai_source
        ).order_by(
            desc('count')
        ).limit(limit).all()

        return [
            {
                'ai_source': ai_source,
                'visit_count': count
            }
            for ai_source, count in results
        ]

    finally:
        db.close()


def get_top_pages(client_id: UUID, limit: int = 10, days: int = 30) -> List[Dict]:
    """
    Get top pages by visit count.

    Args:
        client_id: Client UUID
        limit: Maximum number of results
        days: Number of days to look back

    Returns:
        List of dictionaries with url, page_id, and count
    """
    db = SessionLocal()
    try:
        start_date = datetime.utcnow() - timedelta(days=days)

        results = db.query(
            Visit.url,
            Visit.page_id,
            func.count(Visit.id).label('count')
        ).filter(
            Visit.client_id == client_id,
            Visit.visited_at >= start_date
        ).group_by(
            Visit.url,
            Visit.page_id
        ).order_by(
            desc('count')
        ).limit(limit).all()

        return [
            {
                'url': url,
                'page_id': str(page_id) if page_id else None,
                'count': count
            }
            for url, page_id, count in results
        ]

    finally:
        db.close()


def get_visits_time_series(
    client_id: UUID,
    start_date: datetime,
    end_date: datetime,
    interval: str = 'day'
) -> List[Dict]:
    """
    Get visits time series data with bot crawls and AI referrals separated.

    Args:
        client_id: Client UUID
        start_date: Start date for time series
        end_date: End date for time series
        interval: Interval ('hour', 'day', 'week')

    Returns:
        List of dictionaries with date, bot_crawls, ai_referrals, and direct_visits
    """
    db = SessionLocal()
    try:
        # Determine date truncation based on interval
        if interval == 'hour':
            date_trunc = func.date_trunc('hour', Visit.visited_at)
        elif interval == 'week':
            date_trunc = func.date_trunc('week', Visit.visited_at)
        else:  # default to day
            date_trunc = func.date_trunc('day', Visit.visited_at)

        # Query for bot crawls
        bot_results = db.query(
            date_trunc.label('date'),
            func.count(Visit.id).label('count')
        ).filter(
            Visit.client_id == client_id,
            Visit.visitor_type == 'ai_bot',
            Visit.visited_at >= start_date,
            Visit.visited_at <= end_date
        ).group_by(
            date_trunc
        ).all()

        # Query for AI referrals
        ai_referral_results = db.query(
            date_trunc.label('date'),
            func.count(Visit.id).label('count')
        ).filter(
            Visit.client_id == client_id,
            Visit.visitor_type == 'ai_referral',
            Visit.visited_at >= start_date,
            Visit.visited_at <= end_date
        ).group_by(
            date_trunc
        ).all()

        # Query for direct visits
        direct_results = db.query(
            date_trunc.label('date'),
            func.count(Visit.id).label('count')
        ).filter(
            Visit.client_id == client_id,
            Visit.visitor_type == 'direct',
            Visit.visited_at >= start_date,
            Visit.visited_at <= end_date
        ).group_by(
            date_trunc
        ).all()

        # Combine results
        bot_dict = {date: count for date, count in bot_results}
        ai_referral_dict = {date: count for date, count in ai_referral_results}
        direct_dict = {date: count for date, count in direct_results}

        # Get all unique dates
        all_dates = sorted(set(bot_dict.keys()) | set(ai_referral_dict.keys()) | set(direct_dict.keys()))

        time_series = []
        for date in all_dates:
            bot_crawls = bot_dict.get(date, 0)
            ai_referrals = ai_referral_dict.get(date, 0)
            direct_visits = direct_dict.get(date, 0)

            time_series.append({
                'date': date.isoformat() if date else None,
                'bot_crawls': bot_crawls,
                'ai_referrals': ai_referrals,
                'direct_visits': direct_visits,
                'total_visits': bot_crawls + ai_referrals + direct_visits
            })

        return time_series

    finally:
        db.close()


def get_visit_stats(
    client_id: UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict:
    """
    Get visit statistics for a client with bot crawls and AI referrals separated.

    Args:
        client_id: Client UUID
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        Dictionary with visit statistics
    """
    db = SessionLocal()
    try:
        # Build base query
        query = db.query(Visit).filter(Visit.client_id == client_id)

        # Apply date filters if provided
        if start_date:
            query = query.filter(Visit.visited_at >= start_date)
        if end_date:
            query = query.filter(Visit.visited_at <= end_date)

        # Total visits
        total_visits = query.count()

        # Bot crawls
        bot_crawls = query.filter(Visit.visitor_type == 'ai_bot').count()

        # AI referrals
        ai_referrals = query.filter(Visit.visitor_type == 'ai_referral').count()

        # Direct visits
        direct_visits = query.filter(Visit.visitor_type == 'direct').count()

        # Unique pages visited
        unique_pages = query.with_entities(Visit.url).distinct().count()

        # Calculate percentages
        bot_crawl_percentage = (bot_crawls / total_visits * 100) if total_visits > 0 else 0
        ai_referral_percentage = (ai_referrals / total_visits * 100) if total_visits > 0 else 0
        direct_percentage = (direct_visits / total_visits * 100) if total_visits > 0 else 0

        return {
            'total_visits': total_visits,
            'bot_crawls': bot_crawls,
            'ai_referrals': ai_referrals,
            'direct_visits': direct_visits,
            'unique_pages': unique_pages,
            'bot_crawl_percentage': round(bot_crawl_percentage, 2),
            'ai_referral_percentage': round(ai_referral_percentage, 2),
            'direct_percentage': round(direct_percentage, 2),
            'start_date': start_date.isoformat() if start_date else None,
            'end_date': end_date.isoformat() if end_date else None
        }

    finally:
        db.close()


def get_dashboard_analytics(client_id: UUID, days: int = 30) -> Dict:
    """
    Get comprehensive dashboard analytics with bot crawls and AI referrals separated.

    Args:
        client_id: Client UUID
        days: Number of days to analyze

    Returns:
        Dictionary with comprehensive analytics data
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    end_date = datetime.utcnow()

    # Get basic stats
    stats = get_visit_stats(client_id, start_date, end_date)

    # Get top bot crawlers
    top_bots = get_top_bot_crawlers(client_id, limit=10, days=days)

    # Get top AI sources
    top_ai_sources = get_top_ai_sources(client_id, limit=10, days=days)

    # Get top pages
    top_pages = get_top_pages(client_id, limit=10, days=days)

    # Get time series
    time_series = get_visits_time_series(
        client_id,
        start_date,
        end_date,
        interval='day'
    )

    # Bot crawler breakdown (pie chart data)
    bot_breakdown = []
    for bot in top_bots:
        bot_breakdown.append({
            'name': bot['bot_name'],
            'value': bot['crawl_count']
        })

    # AI source breakdown (pie chart data)
    ai_source_breakdown = []
    for source in top_ai_sources:
        ai_source_breakdown.append({
            'name': source['ai_source'],
            'value': source['visit_count']
        })

    # Page breakdown (bar chart data)
    page_breakdown = []
    for page in top_pages:
        page_breakdown.append({
            'url': page['url'],
            'value': page['count']
        })

    return {
        'summary': stats,
        'time_series': time_series,
        'bot_breakdown': bot_breakdown,
        'ai_source_breakdown': ai_source_breakdown,
        'page_breakdown': page_breakdown,
        'top_bots': top_bots,
        'top_ai_sources': top_ai_sources,
        'top_pages': top_pages,
        'period_days': days
    }


def get_page_visit_stats(page_id: UUID, limit: int = 100) -> Dict:
    """
    Get visit statistics for a specific page.

    Args:
        page_id: Page UUID
        limit: Maximum number of visits to return

    Returns:
        Dictionary with page visit data
    """
    db = SessionLocal()
    try:
        # Get page info
        page = db.query(Page).filter(Page.id == page_id).first()

        if not page:
            raise ValueError(f"Page not found: {page_id}")

        # Get visits
        visits = db.query(Visit).filter(
            Visit.page_id == page_id
        ).order_by(
            desc(Visit.visited_at)
        ).limit(limit).all()

        # Total visits
        total_visits = db.query(Visit).filter(Visit.page_id == page_id).count()

        # Bot crawls
        bot_crawls = db.query(Visit).filter(
            Visit.page_id == page_id,
            Visit.visitor_type == 'ai_bot'
        ).count()

        # AI referrals
        ai_referrals = db.query(Visit).filter(
            Visit.page_id == page_id,
            Visit.visitor_type == 'ai_referral'
        ).count()

        # Direct visits
        direct_visits = db.query(Visit).filter(
            Visit.page_id == page_id,
            Visit.visitor_type == 'direct'
        ).count()

        return {
            'page_id': str(page_id),
            'url': page.url,
            'total_visits': total_visits,
            'bot_crawls': bot_crawls,
            'ai_referrals': ai_referrals,
            'direct_visits': direct_visits,
            'visits': [visit.to_dict() for visit in visits]
        }

    finally:
        db.close()
