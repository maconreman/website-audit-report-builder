"""
Vercel serverless entrypoint.
Wraps the Flask app so Vercel can serve it as a Python serverless function.
All /api/* routes are handled by this function.
"""

import sys
import os

# Add project root to path so backend imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app

app = create_app()

# Vercel expects a WSGI-compatible `app` or a handler function
# The Flask app IS WSGI-compatible, so Vercel picks it up directly.
