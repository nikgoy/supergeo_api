#!/usr/bin/env python3
"""
Application entry point.

Run the Flask development server.
For production, use gunicorn or another WSGI server.
"""
import os
import sys

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.config import settings


def main():
    """Main entry point."""
    app = create_app()

    # Get host and port from environment or use defaults
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))

    print(f"""
╔════════════════════════════════════════════════════════════════╗
║                   AI Cache Layer API                           ║
╚════════════════════════════════════════════════════════════════╝

Environment: {settings.flask_env}
Debug: {settings.debug}
Host: {host}
Port: {port}

Endpoints:
  • Health check: http://{host}:{port}/health
  • API docs: http://{host}:{port}/

🔐 API Key required for protected endpoints
   Set X-API-Key header to your MASTER_API_KEY

Press CTRL+C to stop the server
    """)

    try:
        app.run(
            host=host,
            port=port,
            debug=settings.debug
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
        sys.exit(0)


if __name__ == '__main__':
    main()
