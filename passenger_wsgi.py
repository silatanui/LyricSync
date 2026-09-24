"""Passenger entrypoint for shared hosting deployments."""
import os
import sys

app_dir = os.path.dirname(os.path.abspath(__file__))
if app_dir:
    os.chdir(app_dir)
    sys.path.insert(0, app_dir)

from wsgi import app

application = app
