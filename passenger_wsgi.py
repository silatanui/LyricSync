"""Passenger entrypoint for shared hosting deployments."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from wsgi import app

application = app
