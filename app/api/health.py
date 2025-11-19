"""
Health check endpoint.

Provides basic health status and database connectivity check.

IMPORTANT: When modifying endpoints in this file, update postman_collection.json
"""
from flask import Blueprint, jsonify
from sqlalchemy import text

from app.models.base import SessionLocal

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.

    Returns application status and database connectivity.

    Returns:
        JSON response with status information

    Example:
        GET /health

        Response:
        {
            "status": "healthy",
            "database": "connected",
            "version": "1.0.0"
        }
    """
    status = {
        'status': 'healthy',
        'version': '1.0.0'
    }

    # Check database connectivity
    try:
        if SessionLocal is None:
            status['database'] = 'not_initialized'
            status['status'] = 'degraded'
        else:
            db = SessionLocal()
            try:
                # Simple query to check connectivity
                db.execute(text('SELECT 1'))
                status['database'] = 'connected'
            except Exception as e:
                status['database'] = 'error'
                status['database_error'] = str(e)
                status['status'] = 'unhealthy'
            finally:
                db.close()
    except Exception as e:
        status['database'] = 'error'
        status['error'] = str(e)
        status['status'] = 'unhealthy'

    status_code = 200 if status['status'] == 'healthy' else 503

    return jsonify(status), status_code


@health_bp.route('/ping', methods=['GET'])
def ping():
    """
    Simple ping endpoint.

    Returns:
        JSON response with pong message
    """
    return jsonify({'message': 'pong'}), 200
