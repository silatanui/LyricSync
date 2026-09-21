"""Production WSGI entrypoint for Gunicorn, uWSGI, and reverse proxies."""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
