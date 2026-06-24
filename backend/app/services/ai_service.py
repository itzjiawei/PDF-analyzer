from __future__ import annotations

import base64
import io
import logging
import re
import wave

import httpx

from app.core.config import get_settings


logger = logging.getLogger(__name__)


class AIService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    async def transcribe(self, filename: str, content: bytes, content_type: str) -> str:
        if self.settings.deepgram_api_key:
            try:
                transcript = await self._transcribe_deepgram(content, content_type)
                if transcript:
                    return transcript
            except httpx.HTTPError as exc:
                logger.warning("Deepgram ASR failed; falling back to Gemini transcription: %s", exc)

        if not self.settings.gemini_api_key:
            return "What operational readiness metrics does the uploaded book recommend tracking?"

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                "Transcribe this microphone recording into the user's exact question for a PDF book assistant. "
                                "The recording may include room noise or hesitation. Preserve the intended question in plain English. "
                                "Return only the transcript, without commentary, labels, punctuation notes, or markdown."
                            )
                        },
                        {
                            "inline_data": {
                                "mime_type": content_type or "audio/webm",
                                "data": base64.b64encode(content).decode("utf-8"),
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 160},
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                self._generate_url(self.settings.gemini_transcription_model),
                headers=self._headers(),
                json=payload,
            )
        response.raise_for_status()
        return self._extract_text(response.json()).strip()

    async def _transcribe_deepgram(self, content: bytes, content_type: str) -> str:
        params = {
            "model": self.settings.deepgram_model,
            "language": self.settings.deepgram_language,
            "smart_format": "true",
            "punctuate": "true",
            "filler_words": "false",
        }
        keyterms = [term.strip() for term in self.settings.deepgram_keyterms.split(",") if term.strip()]
        headers = {
            "Authorization": f"Token {self.settings.deepgram_api_key}",
            "Content-Type": content_type or "audio/webm",
        }
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                "https://api.deepgram.com/v1/listen",
                params={**params, "keyterm": keyterms},
                headers=headers,
                content=content,
            )
        response.raise_for_status()
        payload = response.json()
        alternatives = payload.get("results", {}).get("channels", [{}])[0].get("alternatives", [])
        if not alternatives:
            return ""
        return alternatives[0].get("transcript", "").strip()

    async def answer(self, question: str, context_blocks: list[dict]) -> str:
        if not self.settings.gemini_api_key:
            return self._fallback_answer(question, context_blocks)

        context = "\n\n".join(
            f"[Source {i + 1}: {block['chapter_title']}, pages {block['page_start']}-{block['page_end']}]\n{block['content']}"
            for i, block in enumerate(context_blocks)
        )
        prompt = (
            "You are a careful book QA assistant. Answer only from the provided context. "
            "If the context is insufficient, say what is missing. Include brief citations like [Source 1]. "
            "Cite only sources you actually used to support the answer; do not cite loosely related sources. "
            "Use clear short paragraphs or numbered steps, but do not use markdown asterisks or bold formatting.\n\n"
            f"Question: {question}\n\nContext:\n{context}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": self.settings.answer_max_output_tokens,
            },
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(self._generate_url(self.settings.gemini_answer_model), headers=self._headers(), json=payload)
        response.raise_for_status()
        return self._extract_text(response.json()).strip()

    async def synthesize(self, text: str) -> tuple[str | None, str | None]:
        if not self.settings.gemini_api_key:
            return None, None

        spoken_text = self._speech_text(text)[:2400]
        payload = {
            "contents": [{"parts": [{"text": f"Say in a clear professional voice: {spoken_text}"}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {"voiceName": self.settings.gemini_tts_voice}
                    }
                },
            },
        }
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(self._generate_url(self.settings.gemini_tts_model), headers=self._headers(), json=payload)
            response.raise_for_status()
            pcm_base64 = response.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
            wav_bytes = self._pcm_to_wav(base64.b64decode(pcm_base64))
            return base64.b64encode(wav_bytes).decode("utf-8"), "audio/wav"
        except (httpx.HTTPError, KeyError, IndexError) as exc:
            logger.warning("Gemini TTS failed; returning text answer without audio: %s", exc)
            return None, None

    def _headers(self) -> dict[str, str]:
        return {"x-goog-api-key": self.settings.gemini_api_key, "Content-Type": "application/json"}

    def _generate_url(self, model: str) -> str:
        return f"{self.base_url}/{model}:generateContent"

    @staticmethod
    def _extract_text(payload: dict) -> str:
        parts = payload.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        return "".join(part.get("text", "") for part in parts)

    @staticmethod
    def _pcm_to_wav(pcm: bytes, channels: int = 1, rate: int = 24000, sample_width: int = 2) -> bytes:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(channels)
            wav.setsampwidth(sample_width)
            wav.setframerate(rate)
            wav.writeframes(pcm)
        return buffer.getvalue()

    @staticmethod
    def _speech_text(text: str) -> str:
        return re.sub(r"\s*\[Source[^\]]*\]", "", text).replace("*", "").strip()

    @staticmethod
    def _fallback_answer(question: str, context_blocks: list[dict]) -> str:
        if not context_blocks:
            return "I could not find enough evidence in the indexed document to answer that question."
        lead = context_blocks[0]
        return (
            f"Based on the strongest retrieved passage, the book connects your question about '{question}' "
            f"to {lead['chapter_title']} on pages {lead['page_start']}-{lead['page_end']}. "
            "Add a Gemini API key to enable the full LLM-generated answer and spoken response."
        )
