# Audio Transcription Feature

## Overview
Complete audio transcription pipeline using OpenAI Whisper API for the Samvaad Sathi interview platform.

## Features
- ✅ Audio file upload (MP3, WAV, M4A, etc.)
- ✅ OpenAI Whisper transcription with word-level timestamps
- ✅ Question attempt linking
- ✅ Database storage of transcriptions
- ✅ JWT authentication integration
- ✅ Comprehensive error handling

## API Endpoints

### POST /api/transcribe-whisper
Upload and transcribe audio files linked to interview questions.

**Request:**
- `file`: Audio file (multipart/form-data)
- `question_attempt_id`: String (form data) - ID of the question attempt this audio answer belongs to
- `language`: Optional language code (default: "en")

**Response:**
```json
{
  "filename": "audio.mp3",
  "fileSizeBytes": 1155720,
  "durationSeconds": 72.23,
  "transcriptionText": "Your hands lie open...",
  "wordLevelTimestamps": [...],
  "wordCount": 130,
  "whisperModel": "whisper-1",
  "whisperLatencyMs": 6831,
  "saved": true
}
```

## File Structure
```
src/
├── api/routes/audio.py          # Audio API routes
├── models/schemas/audio.py      # Audio request/response schemas
├── models/entities/audio.py     # Database models for audio transcriptions
├── services/whisper.py          # OpenAI Whisper integration
├── services/audio_processor.py  # Audio file processing utilities
└── repository/crud/audio.py     # Database operations for audio
```

## Configuration
Add to your `.env` file:
```
OPENAI_API_KEY=your_openai_api_key
MAX_AUDIO_SIZE_MB=25
OPENAI_MODEL=gpt-4o-mini
```

## Testing
Run the comprehensive smoke test:
```bash
python scripts/smoke_test.py
```

## File Storage
- Audio files are processed completely in memory and temporary files
- No permanent file storage is used - the system is stateless
- Temporary files are automatically cleaned up after processing
- Only transcription metadata is saved to the database

## Performance
- Average transcription time: ~7 seconds for 72-second audio
- Word-level timestamp accuracy: High precision
- Supports files up to 25MB by default
- Asynchronous processing for better API responsiveness
