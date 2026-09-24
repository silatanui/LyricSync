"""Passenger entrypoint for shared hosting deployments."""
import os
import sys
import traceback

# 1. Virtualenv Python interpreter detection for cPanel/CloudLinux
for venv_candidate in [
    os.path.expanduser("~/virtualenv/LyricSync/3.11/bin/python"),
    "/home/ipusgkqs/virtualenv/LyricSync/3.11/bin/python",
]:
    if os.path.exists(venv_candidate) and sys.executable != venv_candidate:
        try:
            os.execl(venv_candidate, venv_candidate, *sys.argv)
        except Exception:
            pass

# 2. Virtualenv site-packages path injection
for site_pkg in [
    os.path.expanduser("~/virtualenv/LyricSync/3.11/lib/python3.11/site-packages"),
    "/home/ipusgkqs/virtualenv/LyricSync/3.11/lib/python3.11/site-packages",
]:
    if os.path.isdir(site_pkg) and site_pkg not in sys.path:
        sys.path.insert(0, site_pkg)

# 3. Application directory setup
app_dir = os.path.dirname(os.path.abspath(__file__))
if app_dir:
    try:
        os.chdir(app_dir)
    except Exception:
        pass
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)

# 4. Import WSGI application with resilient error reporting
try:
    from wsgi import app
    application = app
except Exception as e:
    tb = traceback.format_exc()
    def application(environ, start_response):
        status = '500 Internal Server Error'
        output = f"""<!DOCTYPE html>
<html>
<head><title>LyricSync Startup Error</title></head>
<body style="font-family: monospace; padding: 2rem; background: #fff5f5; color: #900;">
    <h2>LyricSync Application Startup Error</h2>
    <p><b>{e}</b></p>
    <pre style="background: #fff; padding: 1rem; border: 1px solid #fcc; overflow-x: auto;">{tb}</pre>
</body>
</html>""".encode('utf-8')
        response_headers = [('Content-Type', 'text/html; charset=utf-8'), ('Content-Length', str(len(output)))]
        start_response(status, response_headers)
        return [output]
