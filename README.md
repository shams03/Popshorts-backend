# PopShorts Backend

AI-powered API that turns long-form videos into vertical YouTube Shorts.

Upload a video → get transcribed → Gemini/Groq picks viral moments → FFmpeg trims clips → face-aware 9:16 crop → captions + metadata → optional YouTube upload.

## Stack

- **API:** FastAPI + Uvicorn  
- **ASR:** AssemblyAI (word-level timestamps)  
- **LLM:** Google Gemini (`gemini-3.6-flash`) with optional Groq (Llama) fallback  
- **Video:** FFmpeg, OpenCV, MediaPipe  
- **Optional upload:** YouTube Data API v3  

## Quick start

```bash
# Python 3.11 or 3.12 (not 3.14)
cd Hackathon/PopShorts
python3.12 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# System dependency
# brew install ffmpeg   # macOS

cp backend/.env.example backend/.env   # or create .env manually
# Set GEMINI_API_KEY, ASSEMBLYAI_API_KEY (optional: GROQ_API_KEY, HF_TOKEN)

cd backend
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

- Health: http://localhost:8000/health  
- Docs: http://localhost:8000/docs  
- Generated clips: http://localhost:8000/shorts/short_0.mp4  

## Environment

| Variable | Required | Purpose |
|----------|----------|---------|
| `GEMINI_API_KEY` | Yes* | Short extraction + titles/tags |
| `ASSEMBLYAI_API_KEY` | Yes | Transcription |
| `GEMINI_MODEL` | No | Default `gemini-3.6-flash` |
| `GROQ_API_KEY` | No | LLM fallback |
| `LLM_PROVIDER` | No | `auto` \| `gemini` \| `groq` |
| `HF_TOKEN` | No | Speaker diarization (pyannote) |
| `AUTO_UPLOAD_PKL` | No | Path to YouTube OAuth pickle |

\*Or use Groq-only with `LLM_PROVIDER=groq`.

**Do not commit** `.env`, `secrets/`, `*.pkl`, or `backend/shorts/`.

## Main API

`POST /process-video` (multipart)

| Field | Type | Notes |
|-------|------|--------|
| `video` | file | Input video |
| `number_of_shorts` | int | How many clips to generate |
| `auto_upload` | bool | Upload to YouTube if credentials set |
| `mode` | string | Use `sequential` |

## Project layout

```text
PopShorts/
├── backend/
│   ├── app.py              # FastAPI entry
│   ├── main.py             # Processing pipeline
│   ├── features/           # Subtitles, crop, YouTube upload
│   ├── utils/              # LLM, transcription, FFmpeg helpers
│   └── shorts/             # Output videos (gitignored)
├── secrets/                # OAuth credentials (gitignored)
├── Dockerfile
└── README.md
```

## Docker

```bash
docker build -t popshorts-backend .
docker run -p 8000:8000 --env-file backend/.env \
  -v "$(pwd)/backend/shorts:/app/shorts" \
  popshorts-backend
```

## Notes

- Processing is CPU-heavy and can take several minutes — not suited to tiny serverless free tiers.  
- Homebrew FFmpeg may lack `drawtext`; captions fall back to OpenCV/PIL burn-in.  
- Companion frontend lives under `Hackathon-FE/PopShorts-frontend`.
