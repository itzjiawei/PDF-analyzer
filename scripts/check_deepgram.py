import asyncio
import base64
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.ai_service import AIService  # noqa: E402


async def main() -> None:
    ai = AIService()
    if not ai.settings.deepgram_api_key:
        print("deepgram_key_set False")
        return

    # Generate a tiny known WAV with Gemini TTS, then ask Deepgram to transcribe it.
    audio_base64, mime_type = await ai.synthesize("How should teams handle incident readiness?")
    if not audio_base64 or not mime_type:
        print("test_audio_ok False")
        return

    transcript = await ai._transcribe_deepgram(base64.b64decode(audio_base64), mime_type)
    print("deepgram_key_set True")
    print("deepgram_transcription_ok", bool(transcript))
    print("deepgram_transcript_preview", transcript[:140])


if __name__ == "__main__":
    asyncio.run(main())
