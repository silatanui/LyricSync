import os
import sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("LC_ALL", "C.UTF-8")

app_dir = os.path.dirname(os.path.abspath(__file__))
if app_dir and app_dir not in sys.path:
    sys.path.insert(0, app_dir)

# Cache loaded app or capture startup exception
_cached_app = None
_load_error = None

try:
    from wsgi import app as _cached_app
except Exception as _e:
    import traceback
    _load_error = (str(_e), traceback.format_exc())

def application(environ, start_response):
    global _cached_app, _load_error

    if _cached_app is None and _load_error is None:
        try:
            from wsgi import app as loaded_app
            _cached_app = loaded_app
        except Exception as e:
            import traceback
            _load_error = (str(e), traceback.format_exc())

    if _load_error:
        err_msg, tb = _load_error
        # Return HTTP 200 so Apache/Cloudflare error documents don't suppress the traceback!
        status = '200 OK'
        body = f"""<!DOCTYPE html>
<html>
<head><title>LyricSync Startup Error</title></head>
<body style="font-family: monospace; padding: 2rem; background: #fff5f5; color: #900;">
    <h2>LyricSync Application Startup Error</h2>
    <p style="font-size: 1.15rem;"><b>{err_msg}</b></p>
    <pre style="background: #fff; padding: 1.5rem; border: 1px solid #fcc; font-size: 13px; line-height: 1.4; overflow-x: auto;">{tb}</pre>
</body>
</html>""".encode('utf-8')
        response_headers = [
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Content-Length', str(len(body)))
        ]
        start_response(status, response_headers)
        return [body]

    return _cached_app(environ, start_response)
