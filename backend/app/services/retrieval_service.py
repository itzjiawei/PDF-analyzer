from __future__ import annotations

import math
import re
from collections import Counter

import psycopg

from app.core.config import get_settings
from app.services.embedding_service import EmbeddingService, vector_literal
from app.services.text_processing import keywords


class RetrievalService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.embedding_service = EmbeddingService()

    async def retrieve(self, connection: psycopg.Connection, document_id: int, question: str) -> list[dict]:
        embedding = await self.embedding_service.embed(question, task_type="RETRIEVAL_QUERY")
        vector = vector_literal(embedding)
        candidate_count = self.settings.retrieval_candidate_count

        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH dense AS (
                    SELECT id, 1 - (embedding <=> %s::vector) AS dense_score
                    FROM chunks
                    WHERE document_id = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                ),
                sparse AS (
                    SELECT id, ts_rank_cd(search_vector, websearch_to_tsquery('english', %s)) AS sparse_score
                    FROM chunks
                    WHERE document_id = %s AND search_vector @@ websearch_to_tsquery('english', %s)
                    ORDER BY sparse_score DESC
                    LIMIT %s
                )
                SELECT c.id, c.chapter_title, c.chapter_number, c.page_start, c.page_end, c.content,
                       COALESCE(d.dense_score, 0) AS dense_score,
                       COALESCE(s.sparse_score, 0) AS sparse_score
                FROM chunks c
                LEFT JOIN dense d ON c.id = d.id
                LEFT JOIN sparse s ON c.id = s.id
                WHERE c.document_id = %s AND (d.id IS NOT NULL OR s.id IS NOT NULL)
                """,
                (vector, document_id, vector, candidate_count, question, document_id, question, candidate_count, document_id),
            )
            rows = [dict(row) for row in cursor.fetchall()]

        reranked = self._dedupe_repeated_excerpts(self._rerank(question, rows))
        return reranked[: self.settings.retrieval_context_count]

    def _rerank(self, question: str, rows: list[dict]) -> list[dict]:
        query_terms = Counter(keywords(question))
        for row in rows:
            content_terms = Counter(keywords(row["content"]))
            overlap = sum(min(query_terms[t], content_terms[t]) for t in query_terms)
            coverage = overlap / max(1, len(query_terms))
            phrase_bonus = 0.12 if question.lower() in row["content"].lower() else 0
            chapter_bonus = 0.04 if any(term in row["chapter_title"].lower() for term in query_terms) else 0
            dense = float(row.get("dense_score") or 0)
            sparse = float(row.get("sparse_score") or 0)
            row["score"] = round((0.48 * dense) + (0.32 * math.tanh(sparse)) + (0.16 * coverage) + phrase_bonus + chapter_bonus, 4)
            row["excerpt"] = self._excerpt(row["content"], query_terms)
        return sorted(rows, key=lambda item: item["score"], reverse=True)

    @staticmethod
    def _excerpt(content: str, query_terms: Counter) -> str:
        sentences = [sentence.strip() for sentence in content.split(". ") if sentence.strip()]
        if not sentences:
            return content[:260]
        best = max(sentences, key=lambda s: sum(1 for term in query_terms if term in s.lower()))
        return best[:280] + ("..." if len(best) > 280 else "")

    @staticmethod
    def _dedupe_repeated_excerpts(rows: list[dict]) -> list[dict]:
        unique_rows: list[dict] = []
        seen: set[str] = set()
        for row in rows:
            fingerprint = re.sub(r"\W+", " ", row.get("excerpt", "").lower()).strip()
            if fingerprint and fingerprint in seen:
                continue
            if fingerprint:
                seen.add(fingerprint)
            unique_rows.append(row)
        return unique_rows
