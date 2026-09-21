import os
from celery import Celery
from config import Config

def make_celery(app_name=__name__):
    redis_url = os.getenv("REDIS_URL", Config.REDIS_URL)
    celery = Celery(
        app_name,
        broker=redis_url,
        backend=redis_url,
        include=["app.tasks.transcription_tasks", "app.tasks.render_tasks"]
    )
    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
    )
    return celery

celery_app = make_celery("lyricsync")
