import sys
import traceback

sys.path.insert(0, r"c:\Users\silat\Desktop\Projects\Lyric_studio")
from app import create_app
from app.tasks.transcription_tasks import run_transcription_pipeline

app = create_app()
try:
    print("Starting run_transcription_pipeline...")
    run_transcription_pipeline(app, 'proj_1a0c01c7b5f_b357b48b', 'job_1a0c01c9bc0_96d30123')
    print("run_transcription_pipeline finished!")
except Exception as e:
    print("Exception occurred:")
    traceback.print_exc()
