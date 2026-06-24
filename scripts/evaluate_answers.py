import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.ai_service import AIService  # noqa: E402
from app.services.retrieval_service import RetrievalService  # noqa: E402


@dataclass
class GoldenQuestion:
    question: str
    expected_chapter: int
    expected_terms: list[str]


GOLDEN_QUESTIONS = [
    GoldenQuestion(
        question="Why does the handbook recommend hybrid search and reranking?",
        expected_chapter=3,
        expected_terms=["dense vectors", "keyword search", "recall", "reranking"],
    ),
    GoldenQuestion(
        question="What should answer quality evaluation check?",
        expected_chapter=7,
        expected_terms=["retrieval hit rate", "citation faithfulness", "unsupported claims"],
    ),
    GoldenQuestion(
        question="How should the voice experience be designed?",
        expected_chapter=8,
        expected_terms=["transcript", "audio", "turns"],
    ),
    GoldenQuestion(
        question="What governance controls does the handbook recommend?",
        expected_chapter=4,
        expected_terms=["policy", "approvals", "audit"],
    ),
    GoldenQuestion(
        question="What metrics should teams track for signal quality?",
        expected_chapter=1,
        expected_terms=["latency", "freshness", "precision", "recall"],
    ),
]


async def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate RAG retrieval and answer quality on golden questions.")
    parser.add_argument("--document-id", type=int, default=None, help="Document id to evaluate. Defaults to latest indexed document.")
    parser.add_argument("--retrieval-only", action="store_true", help="Skip Gemini answer calls and evaluate retrieval only.")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set. Run: set -a && source .env && set +a")

    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        document_id = args.document_id or latest_document_id(connection)
        if not document_id:
            raise SystemExit("No indexed documents found. Upload the sample PDF first.")

        print(f"Evaluating document_id={document_id}")
        print("=" * 72)

        retrieval_service = RetrievalService()
        ai_service = AIService()
        passed = 0

        for index, golden in enumerate(GOLDEN_QUESTIONS, start=1):
            retrieved = await retrieval_service.retrieve(connection, document_id, golden.question)
            retrieved_chapters = [row["chapter_number"] for row in retrieved[:3]]
            chapter_pass = golden.expected_chapter in retrieved_chapters

            answer = ""
            keyword_hits: list[str] = []
            if not args.retrieval_only:
                answer = await ai_service.answer(golden.question, retrieved)
                answer_lower = answer.lower()
                keyword_hits = [term for term in golden.expected_terms if term.lower() in answer_lower]
            keyword_pass = args.retrieval_only or len(keyword_hits) >= max(1, min(2, len(golden.expected_terms)))

            case_pass = chapter_pass and keyword_pass
            passed += int(case_pass)

            print(f"{index}. {'PASS' if case_pass else 'FAIL'} - {golden.question}")
            print(f"   Expected chapter: {golden.expected_chapter}")
            print(f"   Top-3 retrieved chapters: {retrieved_chapters}")
            print(f"   Retrieval: {'PASS' if chapter_pass else 'FAIL'}")
            if args.retrieval_only:
                print("   Answer keywords: skipped")
            else:
                print(f"   Expected keyword hits: {keyword_hits or 'none'}")
                print(f"   Answer: {compact(answer)}")
            print()

        total = len(GOLDEN_QUESTIONS)
        print("=" * 72)
        print(f"Score: {passed}/{total} passed")
        if passed == total:
            print("Overall: PASS")
        else:
            print("Overall: REVIEW NEEDED")


def latest_document_id(connection: psycopg.Connection) -> int | None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT id FROM documents WHERE status LIKE 'indexed%' ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        return row["id"] if row else None


def compact(text: str, limit: int = 220) -> str:
    cleaned = " ".join(text.split())
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 3] + "..."


if __name__ == "__main__":
    asyncio.run(main())
