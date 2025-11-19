"""
Flask application factory.

Creates and configures the Flask application with all blueprints and extensions.
"""
import os
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from app.config import settings
from app.models.base import init_db


def create_app(config_override: dict = None) -> Flask:
    """
    Create and configure the Flask application.

    Args:
        config_override: Optional dictionary to override settings

    Returns:
        Configured Flask application instance

    Usage:
        app = create_app()
        app.run()
    """
    app = Flask(__name__)

    # Configure Flask
    app.config['SECRET_KEY'] = settings.secret_key
    app.config['DEBUG'] = settings.debug
    app.config['ENV'] = settings.flask_env

    # Apply any config overrides (useful for testing)
    if config_override:
        app.config.update(config_override)

    # Initialize database
    try:
        database_url = settings.get_database_url()
        init_db(database_url)
        print(f"Database initialized successfully")
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}")
        print("The application will start but database operations will fail.")
        print("Please ensure DATABASE_URL is set correctly in your .env file")

    # Register blueprints
    from app.api import health_bp, clients_bp, sitemap_bp
    app.register_blueprint(health_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(sitemap_bp)

    # Register error handlers
    register_error_handlers(app)

    # Add CORS headers for API responses
    @app.after_request
    def after_request(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,X-API-Key'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,PATCH,DELETE,OPTIONS'
        return response

    @app.route('/')
    def index():
        """Root endpoint with API information."""
        return jsonify({
            'name': 'AI Cache Layer API',
            'version': '1.0.0',
            'description': 'AI-friendly caching layer for websites',
            'endpoints': {
                'health': '/health',
                'ping': '/ping',
                'clients': '/api/v1/clients',
                'sitemap': '/api/v1/sitemap',
            },
            'documentation': 'https://github.com/yourusername/ai-cache-layer',
        })

    return app


def register_error_handlers(app: Flask) -> None:
    """
    Register global error handlers.

    Args:
        app: Flask application instance
    """

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """Handle HTTP exceptions."""
        return jsonify({
            'error': e.name,
            'message': e.description,
            'status_code': e.code
        }), e.code

    @app.errorhandler(Exception)
    def handle_exception(e):
        """Handle unexpected exceptions."""
        app.logger.error(f"Unhandled exception: {str(e)}", exc_info=True)

        # Don't reveal internal errors in production
        if settings.is_production:
            return jsonify({
                'error': 'Internal server error',
                'message': 'An unexpected error occurred'
            }), 500
        else:
            return jsonify({
                'error': 'Internal server error',
                'message': str(e),
                'type': type(e).__name__
            }), 500

    @app.errorhandler(404)
    def handle_not_found(e):
        """Handle 404 errors."""
        return jsonify({
            'error': 'Not found',
            'message': 'The requested resource was not found'
        }), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        """Handle 405 errors."""
        return jsonify({
            'error': 'Method not allowed',
            'message': 'The method is not allowed for the requested URL'
        }), 405
