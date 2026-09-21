import os
import threading
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any

logger = logging.getLogger(__name__)

# Dedicated thread pool for async background execution when Celery is not running
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="lyricsync-worker")

def submit_task(task_func: Callable, *args, **kwargs):
    """
    Submits a background task to the executor.
    Runs asynchronously and does not block Flask HTTP requests.
    """
    try:
        return _executor.submit(task_func, *args, **kwargs)
    except Exception as e:
        logger.error(f"Failed to submit background task: {e}")
        raise
