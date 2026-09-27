import base64
from fastapi import APIRouter, UploadFile, File, HTTPException, Response
from pydantic import BaseModel
from app.services.voice_service import voice_service

router = APIRouter(prefix="/voice", tags=["Voice STT & TTS"])

class TTSRequest(BaseModel):
    text: str
    voice: str = "en-US-ChristopherNeural"

class TranscribeResponse(BaseModel):
    text: str
    confidence: float = 0.96

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio_endpoint(file: UploadFile = File(...)):
    """Transcribes uploaded voice audio using Whisper."""
    try:
        content = await file.read()
        text = await voice_service.transcribe_audio(content, file.filename)
        return TranscribeResponse(text=text, confidence=0.96)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio transcription failed: {e}")

@router.post("/synthesize")
async def synthesize_speech_endpoint(payload: TTSRequest):
    """Synthesizes text into streaming voice audio."""
    try:
        audio_bytes = await voice_service.synthesize_speech(payload.text)
        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={"Content-Disposition": "inline; filename=speech.wav"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {e}")
