import uuid
import time

def generate_id(prefix: str = "id") -> str:
    """Generate an opaque, ordered identifier with a prefix."""
    ts = hex(int(time.time() * 1000))[2:]
    rand = uuid.uuid4().hex[:8]
    return f"{prefix}_{ts}_{rand}"

def generate_project_id() -> str:
    return generate_id("proj")

def generate_asset_id() -> str:
    return generate_id("asset")

def generate_job_id() -> str:
    return generate_id("job")

def generate_user_id() -> str:
    return generate_id("usr")
