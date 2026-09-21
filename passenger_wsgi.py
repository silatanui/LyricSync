"""
WSGI entry point for cPanel's "Setup Python App" (Passenger).

cPanel creates this file automatically when you set up the Python App; replace
its generated contents with this file so Passenger serves the Flask app.
Passenger sets SCRIPT_NAME/PASSENGER_BASE_URI automatically for the configured
"Application URL" (e.g. tanuisila.dev/LyricSync), so no extra subpath config
is required in the Flask app itself.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

application = create_app()
