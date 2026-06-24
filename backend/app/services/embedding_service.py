from __future__ import annotations

import hashlib
import math

import httpx
import numpy as np

from app.core.config import get_settings
from app.services.text_processing import keywords


class EmbeddingService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def embed(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
        if self.settings.gemini_api_key:
            try:
                return await self._embed_gemini(text, task_type)
            except Exception:
                return self._embed_hashing(text)
        return self._embed_hashing(text)

    async def _embed_gemini(self, text: str, task_type: str) -> list[float]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.settings.gemini_embedding_model}:embedContent"
        headers = {"x-goog-api-key": self.settings.gemini_api_key, "Content-Type": "application/json"}
        payload = {
            "content": {"parts": [{"text": text[:6000]}]},
            "task_type": task_type,
            "output_dimensionality": self.settings.embedding_dimensions,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            payload = response.json()

        values = payload.get("embedding", {}).get("values", [])
        vector = np.array(values, dtype=float)[: self.settings.embedding_dimensions]
        if vector.shape[0] < self.settings.embedding_dimensions:
            vector = np.pad(vector, (0, self.settings.embedding_dimensions - vector.shape[0]))
        return self._normalize(vector).tolist()

    def _embed_hashing(self, text: str) -> list[float]:
        vector = np.zeros(self.settings.embedding_dimensions, dtype=float)
        for word in keywords(text):
            digest = hashlib.sha256(word.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.settings.embedding_dimensions
            sign = 1 if digest[4] % 2 == 0 else -1
            vector[bucket] += sign * (1.0 + math.log1p(len(word)))
        return self._normalize(vector).tolist()

    @staticmethod
    def _normalize(vector: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector
        return vector / norm


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"
