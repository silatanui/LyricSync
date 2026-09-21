import os
import time
from pathlib import Path
from config import Config

class StorageCleanupService:
    @staticmethod
    def cleanup_old_temp_files(max_age_hours: int = 24):
        """Removes temporary files older than max_age_hours."""
        now = time.time()
        cutoff = now - (max_age_hours * 3600)
        
        if Config.TEMP_ROOT.exists():
            for item in Config.TEMP_ROOT.glob("*"):
                if item.is_file():
                    try:
                        if item.stat().st_mtime < cutoff:
                            item.unlink()
                    except Exception:
                        pass
