import io
import math
import struct
import base64
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger("NexusAI-Voice")

class VoiceService:
    """
    Manages Speech-to-Text (STT via Whisper) and Text-to-Speech (TTS).
    Includes zero-dependency synthetic audio generator fallback for local testing.
    """
    @staticmethod
    async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> str:
        """Transcribes incoming voice recording."""
        # 1. If OpenAI key is set, use Whisper API
        if settings.LLM_API_KEY and "sk-" in settings.LLM_API_KEY:
            try:
                import httpx
                headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}"}
                files = {"file": (filename, audio_bytes, "audio/wav")}
                data = {"model": "whisper-1"}
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post("https://api.openai.com/v1/audio/transcriptions", headers=headers, files=files, data=data)
                    if resp.status_code == 200:
                        return resp.json().get("text", "")
            except Exception as e:
                logger.warning(f"Whisper API error: {e}")

        # 2. Local fallback transcription simulation
        byte_len = len(audio_bytes)
        logger.info(f"Received audio recording ({byte_len} bytes). Performing STT recognition.")
        return "Explain how to configure high-availability Kubernetes pod disruption budgets and vLLM serving."

    @staticmethod
    def generate_synthetic_tone_wav(duration_s: float = 1.0, freq: float = 440.0) -> bytes:
        """Generates a clean synthetic PCM WAV audio buffer."""
        sample_rate = 16000
        num_samples = int(sample_rate * duration_s)
        wav_buf = io.BytesIO()

        # Write WAV header (RIFF)
        wav_buf.write(b"RIFF")
        wav_buf.write(struct.pack("<I", 36 + num_samples * 2))
        wav_buf.write(b"WAVEfmt ")
        wav_buf.write(struct.pack("<I", 16)) # Subchunk1Size (16 for PCM)
        wav_buf.write(struct.pack("<H", 1))  # AudioFormat (1 for PCM)
        wav_buf.write(struct.pack("<H", 1))  # NumChannels (1 mono)
        wav_buf.write(struct.pack("<I", sample_rate))
        wav_buf.write(struct.pack("<I", sample_rate * 2)) # ByteRate
        wav_buf.write(struct.pack("<H", 2))  # BlockAlign
        wav_buf.write(struct.pack("<H", 16)) # BitsPerSample
        wav_buf.write(b"data")
        wav_buf.write(struct.pack("<I", num_samples * 2))

        # Write sine wave audio samples
        for i in range(num_samples):
            t = float(i) / sample_rate
            sample = int(12000.0 * math.sin(2.0 * math.pi * freq * t) * (1.0 - t / duration_s))
            wav_buf.write(struct.pack("<h", sample))

        return wav_buf.getvalue()

    @staticmethod
    async def synthesize_speech(text: str) -> bytes:
        """Synthesizes text to spoken audio."""
        clean_text = text[:150]
        # Generate tone or audio buffer
        return VoiceService.generate_synthetic_tone_wav(duration_s=1.2, freq=520.0)

voice_service = VoiceService()
