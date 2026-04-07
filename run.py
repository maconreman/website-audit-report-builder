#!/usr/bin/env python3
"""
Run the Website Audit Report Builder.
Single entry point — starts the Flask backend.
"""

import sys
import os

# Ensure project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app import create_app
from backend.config import HOST, PORT, DEBUG


def main():
    print("=" * 55)
    print("  Website Audit Report Builder — Phase 1")
    print("=" * 55)
    print(f"  Backend:  http://localhost:{PORT}")
    print(f"  API Docs: http://localhost:{PORT}/")
    print(f"  Status:   http://localhost:{PORT}/api/status")
    print("=" * 55)
    print()

    app = create_app()
    app.run(host=HOST, port=PORT, debug=DEBUG)


if __name__ == "__main__":
    main()
