# LyricSync Studio

Automated audio-to-video synchronization, word-level temporal alignment, and subtitle rendering engine.

---

## Overview

LyricSync Studio is a web-based production suite designed to transform recorded music tracks into synchronized, broadcast-quality lyric videos. The system analyzes raw musical audio, generates millisecond-accurate word timestamps via speech recognition models, groups words into musical phrases based on vocal pauses and punctuation, and composites vector-rendered typography onto video or image backgrounds using single-pass FFmpeg filtergraphs.

The application is engineered to operate efficiently on standard CPU hosting infrastructure without mandatory GPU hardware, featuring dual-tier rendering modes for both instant draft previews and studio-grade master exports.

---

## Key Features

- Automated Word-Level Temporal Alignment: Ingests audio files and queries OpenAI Whisper with word timestamp granularities enabled. Gaps between consecutive words are automatically interpolated to eliminate jarring subtitle disappearances.
- Musical Line Grouping: Automatically segments continuous speech tokens into discrete lyric lines using vocal pause detection (inter-word gap threshold of 0.45 seconds), terminal punctuation boundaries, and line-length constraints.
- Vector Subtitle Generation: Generates native Advanced SubStation Alpha (.ass) scripts rather than rasterized images. Timing tags enable smooth sub-frame syllable highlighting and precise typographic control.
- Dual-Tier Rendering Engine:
  - 720p Fast Draft: Renders at 1280x720 using H.264 CRF 23, the veryfast preset, and 128 kbps AAC audio for near-instant browser previews and bandwidth-constrained mobile devices.
  - 1080p Studio Master: Renders at 1920x1080 using H.264 CRF 20, the medium preset, and 192 kbps AAC audio for high-fidelity master delivery.
  - MP4 Progressive Streaming: All output containers are compiled with the faststart flag, placing the moov atom at the beginning of the file for immediate web streaming without waiting for complete downloads.
- Interactive Timeline Studio: Browser-based editor featuring bidirectional scrubbing. Scrubbing the audio player immediately updates timeline chips and preview canvases; clicking any lyric chip jumps playback to its exact timestamp.
- Role-Based Access Control: Protects administrative diagnostics, table structures, disk usage, and model parameters so only authorized administrators can view technical server internals. Standard users receive a clean, simplified status view.
- In-App Architecture Documentation: Includes an Astro Starlight-inspired documentation portal (/docs) featuring 7 interactive Mermaid architectural diagrams and copyable, sanitized source implementations rendered in the Outfit typeface.

---

## Architecture and Pipeline

The application processes media through four sequential pipeline phases:

1. Ingestion and Media Safety Probe: Uploaded audio and background media files are analyzed using FFprobe in an error-tolerant UTF-8 subprocess. Durations, streams, codecs, and container dimensions are verified before database persistence.
2. AI Transcription and Segmentation: Audio is processed through the transcription service. Tokenized word boundaries are evaluated through the line segmentation algorithm to establish coherent visual phrasing.
3. Vector Subtitle Compilation: Lyric lines, word durations, typographic styles, margins, and color schemes are assembled into an ASS script file.
4. Single-Pass FFmpeg Synthesis: Video background streams, audio tracks, and ASS subtitle scripts are merged into an H.264/AAC MP4 container in a single command, eliminating intermediate uncompressed frame buffers.

---

## Technology Stack

- Backend Framework: Python 3.10+, Flask 3.0+
- Database and ORM: SQLAlchemy 2.0+, PyMySQL, SQLite (development) / MySQL (production)
- Media Processing: FFmpeg (libx264, aac, libass), FFprobe, ImageIO-FFmpeg, Pillow
- AI and Speech Alignment: OpenAI Whisper API (verbose_json with word granularities)
- Authentication: Flask-Login, Authlib (Google OAuth 2.0 OpenID Connect), Cryptography
- Background Workers: Celery 5.3+, Redis (optional for asynchronous queuing)
- Frontend: Vanilla JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons, Mermaid.js
- Typography: Outfit Google Font (primary interface and documentation)
- Testing: Pytest, AnyIO

---

## Directory Structure

```
Lyric_studio/
|-- app/
|   |-- __init__.py              # Application factory and blueprint registration
|   |-- celery_app.py            # Celery background worker configuration
|   |-- extensions.py            # SQLAlchemy, Flask-Login, and Authlib instances
|   |-- models/
|   |   |-- lyric_line.py        # Lyric line and word timestamp models
|   |   |-- media_asset.py       # Audio, video, and image asset metadata
|   |   |-- project.py           # Project entity and canonical JSON management
|   |   |-- render_job.py        # Render task tracking and status history
|   |   `-- user.py              # User account and authentication model
|   |-- routes/
|   |   |-- api.py               # REST API endpoints (projects, upload, render)
|   |   |-- auth.py              # Google OAuth login, avatar initials, and logout
|   |   `-- views.py             # Server-rendered pages (home, editor, docs, health)
|   |-- services/
|   |   |-- alignment.py         # Word interpolation and musical line segmentation
|   |   |-- ffmpeg.py            # FFmpeg render command builder and execution
|   |   |-- lyrics_importer.py   # Plaintext and LRC file parser
|   |   |-- media_probe.py       # FFprobe metadata extraction utility
|   |   |-- openai_transcription.py # Whisper API client with word timestamps
|   |   |-- subtitles.py         # Advanced SubStation Alpha (.ass) generator
|   |   `-- visual_generator.py  # Fallback background canvas generation
|   |-- tasks/                   # Celery asynchronous tasks
|   `-- utils/                   # ID generators and helper functions
|-- static/
|   |-- css/
|   |   |-- docs.css             # Astro-style documentation layout and Outfit font
|   |   |-- editor.css           # Timeline and canvas studio styles
|   |   `-- main.css             # Base application theme and typography
|   `-- js/
|       |-- api.js               # Client API wrapper
|       |-- editor.js            # Studio timeline synchronization engine
|       `-- upload.js            # Media upload dropzone handler
|-- templates/
|   |-- base.html                # Base layout with navbar, avatar initials, and legal footer
|   |-- dashboard.html           # Project management dashboard
|   |-- docs.html                # Comprehensive documentation page with 7 diagrams
|   |-- editor.html              # Synchronized studio editor
|   |-- home.html                # Landing page with documentation showcase
|   `-- upload.html              # Project upload workflow
|-- tests/                       # Complete Pytest test suite (37 tests)
|-- config.py                    # Environment configuration loader
|-- passenger_wsgi.py            # Phusion Passenger entrypoint for cPanel hosting
|-- requirements.txt             # Production Python dependencies
`-- wsgi.py                      # Standard WSGI entrypoint for Gunicorn
```

---

## Installation and Local Setup

### 1. Prerequisites

Ensure the following tools are installed on your workstation:
- Python 3.10 or higher
- FFmpeg and FFprobe compiled with libass support
- Git

Verify FFmpeg availability in your terminal:
```bash
ffmpeg -version
ffprobe -version
```

### 2. Clone the Repository

```bash
git clone https://github.com/silatanui/LyricSync.git
cd LyricSync
```

### 3. Create a Virtual Environment

On Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

On Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 4. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Copy the example environment file and configure your local settings:
```bash
cp .env.example .env
```

Edit `.env` with your preferred text editor:
```ini
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=change-this-to-a-secure-random-string

# Database Configuration (Leave DATABASE_URL blank to use SQLite in development)
DATABASE_URL=sqlite:///data/lyricsync.db

# Storage Directories
DATA_ROOT=data
MEDIA_ROOT=data/media
OUTPUT_ROOT=data/outputs
TEMP_ROOT=data/temp

# Speech Recognition (Leave empty or set to 'mock' for local offline testing)
OPENAI_API_KEY=
OPENAI_TRANSCRIPTION_MODEL=whisper-1

# Google OAuth (Optional for local testing)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

### 6. Run Database Migrations and Start the Development Server

```bash
flask run --host=127.0.0.1 --port=5000
```

Access the studio at `http://127.0.0.1:5000`.

---

## Environment Variables Reference

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `SECRET_KEY` | `dev-secret-key-lyricsync-2026` | Flask session encryption key. |
| `FLASK_ENV` | `development` | Environment mode (`development` or `production`). |
| `FLASK_DEBUG` | `True` | Enables interactive debugging and automatic reloading. |
| `DATABASE_URL` | Auto-constructed from MySQL params | Full SQLAlchemy database connection string. |
| `MYSQL_HOST` | `localhost` | Hostname for the MySQL database server. |
| `MYSQL_PORT` | `3306` | Port for the MySQL database server. |
| `MYSQL_USER` | `root` | Database username. |
| `MYSQL_PASSWORD` | `""` | Database password. |
| `MYSQL_DATABASE` | `lyricsync_studio` | Database schema name. |
| `OPENAI_API_KEY` | `""` | OpenAI API secret key for Whisper transcription. |
| `OPENAI_TRANSCRIPTION_MODEL` | `whisper-1` | Model identifier for speech-to-text processing. |
| `GOOGLE_CLIENT_ID` | `""` | Google Cloud OAuth 2.0 Web Client ID. |
| `GOOGLE_CLIENT_SECRET` | `""` | Google Cloud OAuth 2.0 Client Secret. |
| `FFMPEG_BINARY` | Auto-detected | Explicit filesystem path to the FFmpeg executable. |
| `FFPROBE_BINARY` | Auto-detected | Explicit filesystem path to the FFprobe executable. |
| `MAX_CONTENT_LENGTH` | `629145600` (600 MB) | Maximum allowable payload size for uploads. |
| `UPLOAD_MAX_AUDIO_MB` | `100` | Maximum size in megabytes for audio file uploads. |
| `UPLOAD_MAX_VIDEO_MB` | `500` | Maximum size in megabytes for background video files. |

---

## Running the Automated Test Suite

LyricSync Studio includes automated test coverage spanning audio probing, transcription parsers, subtitle generators, dual-tier FFmpeg renders, authentication, and documentation endpoints.

Execute the test suite with standard I/O capture disabled:
```bash
pytest tests/ -s -v
```

To run a specific test module:
```bash
pytest tests/test_docs.py -v
pytest tests/test_rendering.py -s -v
```

---

## Production Deployment

### cPanel / Phusion Passenger (CloudLinux / Apache)

LyricSync Studio includes native support for cPanel Python Applications via Phusion Passenger:

1. Configure Python in the cPanel Setup Python App interface, pointing Application startup file to `passenger_wsgi.py`.
2. Connect via SSH or cPanel Terminal and pull the latest code:
   ```bash
   cd ~/LyricSync
   git pull origin main
   ```
3. Activate the virtual environment and ensure all dependencies are installed:
   ```bash
   source ~/virtualenv/LyricSync/3.10/bin/activate
   pip install -r requirements.txt
   ```
4. Restart the Passenger process:
   ```bash
   touch tmp/restart.txt
   ```

### Gunicorn and Nginx (VPS / Linux Server)

For dedicated Linux virtual private servers:
```bash
gunicorn --bind 0.0.0.0:8000 --workers 4 --timeout 120 wsgi:application
```

Configure Nginx as a reverse proxy passing client requests to `http://127.0.0.1:8000` with streaming upload timeouts configured.

---

## Security Model

- Sensitive Credentials: API keys, database credentials, and secret salts are never committed to version control and are strictly loaded through environment variables.
- Path Traversal Mitigation: Media asset paths are generated using cryptographic identifiers and strictly verified within the application data root.
- Technical Diagnostic Guard: Server health diagnostics on `/health` omit environment variables, server directory paths, and database schema tables unless requested by the authorized system administrator.

---

## Authors and Maintainers

Developed by Silas Tanui.
Portfolio and Contact: https://tanuisila.dev

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.