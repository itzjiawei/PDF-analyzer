import asyncio
import base64
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.ai_service import AIService  # noqa: E402
from app.services.embedding_service import EmbeddingService  # noqa: E402


async def main() -> None:
    embedding = await EmbeddingService()._embed_gemini(
        "retrieval quality for a PDF book assistant",
        "RETRIEVAL_QUERY",
    )
    print("gemini_embedding_length", len(embedding))

    ai = AIService()
    answer = await ai.answer(
        "What does the sample say about traceability?",
        [
            {
                "chapter_title": "Chapter 1: Signal Quality",
                "page_start": 2,
                "page_end": 2,
                "content": "The operating standard is to make every answer traceable to a page, chapter, and concrete passage.",
            }
        ],
    )
    print("answer_ok", bool(answer.strip()))
    print("answer_preview", answer[:160].replace("\n", " "))

    audio, mime_type = await ai.synthesize("This is a short test answer.")
    print("tts_ok", bool(audio), mime_type)
    if audio and mime_type:
        transcript = await ai.transcribe("gemini-check.wav", base64.b64decode(audio), mime_type)
        print("transcription_ok", bool(transcript.strip()))
        print("transcription_preview", transcript[:120].replace("\n", " "))


if __name__ == "__main__":
    asyncio.run(main())
