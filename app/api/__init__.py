"""API blueprints package."""
from app.api.health import health_bp
from app.api.clients import clients_bp
from app.api.sitemap import sitemap_bp
from app.api.page_analytics import page_analytics_bp
from app.api.apify import apify_bp
from app.api.gemini import gemini_bp
from app.api.cloudflare_kv import cloudflare_kv_bp
from app.api.cloudflare_worker import cloudflare_worker_bp
from app.api.status import status_bp
from app.api.llms_txt import llms_txt_bp

__all__ = [
    "health_bp",
    "clients_bp",
    "sitemap_bp",
    "page_analytics_bp",
    "apify_bp",
    "gemini_bp",
    "cloudflare_kv_bp",
    "cloudflare_worker_bp",
    "status_bp",
    "llms_txt_bp",
]
