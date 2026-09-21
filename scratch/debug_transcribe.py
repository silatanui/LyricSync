import sys
from pathlib import Path

sys.path.insert(0, r"c:\Users\silat\Desktop\Projects\Lyric_studio")
from app import create_app, db
from app.models.project import Project
from app.services.openai_transcription import OpenAITranscriber

app = create_app()
with app.app_context():
    p = db.session.get(Project, 'proj_1a0c01c7b5f_b357b48b')
    print("Project name:", p.name)
    print("Audio path:", p.audio_path)
    
    transcriber = OpenAITranscriber()
    print("API Key present:", bool(transcriber.api_key))
    print("API Key prefix:", transcriber.api_key[:10] if transcriber.api_key else "None")
    print("Model:", transcriber.model)
    
    try:
        res = transcriber.transcribe_word_timestamps(p.audio_path)
        print("Success! Words count:", len(res.get('words', [])))
        print("First 3 words:", res.get('words', [])[:3])
    except Exception as e:
        import traceback
        print("FAILED WITH EXCEPTION:")
        traceback.print_exc()
