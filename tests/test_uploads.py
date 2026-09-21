from pathlib import Path
from app.utils.validation import validate_audio_file, validate_video_file
from app.utils.files import calculate_checksum, detect_mime_type

def test_validate_audio_extensions():
    assert validate_audio_file("track.mp3", 1024)[0] is True
    assert validate_audio_file("track.wav", 1024)[0] is True
    assert validate_audio_file("track.flac", 1024)[0] is True
    assert validate_audio_file("track.exe", 1024)[0] is False
    assert validate_audio_file("track.txt", 1024)[0] is False

def test_validate_video_extensions():
    assert validate_video_file("clip.mp4", 1024)[0] is True
    assert validate_video_file("clip.mov", 1024)[0] is True
    assert validate_video_file("clip.webm", 1024)[0] is True
    assert validate_video_file("clip.pdf", 1024)[0] is False

def test_size_limits():
    # 200MB audio exceeds default 100MB limit
    is_ok, err = validate_audio_file("track.mp3", 200 * 1024 * 1024)
    assert is_ok is False
    assert "exceeds maximum size" in err

def test_checksum_and_mime(tmp_path):
    f = tmp_path / "sample.mp3"
    f.write_bytes(b"ID3dummydata12345")
    cs = calculate_checksum(f)
    assert len(cs) == 64
    assert detect_mime_type(f) == "audio/mpeg"

def test_derive_title_from_filename():
    from app.routes.uploads import derive_title_from_filename
    assert derive_title_from_filename("01 - Amazing_Grace.mp3") == "Amazing Grace"
    assert derive_title_from_filename("In-The-Arms-Of-Grace_v2.wav") == "In The Arms Of Grace V2"
    assert derive_title_from_filename("Bohemian_Rhapsody (Official Audio).flac") == "Bohemian Rhapsody"
    assert derive_title_from_filename("track.mp3") == "Untitled Song"
    assert derive_title_from_filename("") == "Untitled Song"
