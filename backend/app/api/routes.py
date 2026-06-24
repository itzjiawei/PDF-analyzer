from pathlib import Path
import re
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from psycopg import Connection

from app.db.database import get_connection
from app.models.schemas import (
    AskResponse,
    AskTextRequest,
    Citation,
    DocumentOut,
    EvaluationCaseOut,
    EvaluationResponse,
    HealthResponse,
    TranscribeResponse,
)
from app.services.ai_service import AIService
from app.services.indexing_service import IndexingService
from app.services.retrieval_service import RetrievalService

router = APIRouter()

SAMPLE_EVALUATION_TITLE = "Aurora Operations Handbook"

GOLDEN_QUESTIONS = [
    {
        "question": "Why does the handbook recommend hybrid search and reranking?",
        "expected_chapter": 3,
        "expected_terms": ["dense vectors", "keyword search", "recall", "reranking"],
    },
    {
        "question": "What should answer quality evaluation check?",
        "expected_chapter": 7,
        "expected_terms": ["retrieval hit rate", "citation faithfulness", "unsupported claims"],
    },
    {
        "question": "How should the voice experience be designed?",
        "expected_chapter": 8,
        "expected_terms": ["transcript", "audio", "turns"],
    },
    {
        "question": "What governance controls does the handbook recommend?",
        "expected_chapter": 4,
        "expected_terms": ["policy", "approvals", "audit"],
    },
    {
        "question": "What metrics should teams track for signal quality?",
        "expected_chapter": 1,
        "expected_terms": ["latency", "freshness", "precision", "recall"],
    },
]


@router.get("/health", response_model=HealthResponse)
def health(connection: Connection = Depends(get_connection)):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return HealthResponse(status="ok", database="connected", ai_provider="gemini")


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(connection: Connection = Depends(get_connection)):
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, filename, title, chapter_count, page_count, status FROM documents ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]


@router.post("/documents/upload", response_model=DocumentOut)
async def upload_document(file: UploadFile = File(...), connection: Connection = Depends(get_connection)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Upload a PDF file.")

    suffix = Path(file.filename).suffix
    with NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        temp.write(await file.read())
        temp_path = Path(temp.name)

    try:
        document = await IndexingService().index_pdf(connection, temp_path, file.filename)
        if document["chapter_count"] < 10:
            document["status"] = "indexed_warning_less_than_10_chapters"
        return document
    finally:
        temp_path.unlink(missing_ok=True)


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: int, connection: Connection = Depends(get_connection)):
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM documents WHERE id = %s RETURNING id", (document_id,))
        deleted = cursor.fetchone()
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")
    connection.commit()


@router.post("/ask/text", response_model=AskResponse)
async def ask_text(payload: AskTextRequest, connection: Connection = Depends(get_connection)):
    return await _answer(connection, payload.document_id, payload.question, payload.speak)


@router.post("/ask/voice", response_model=AskResponse)
async def ask_voice(
    document_id: int = Form(...),
    audio: UploadFile = File(...),
    connection: Connection = Depends(get_connection),
):
    content = await audio.read()
    question = await AIService().transcribe(audio.filename or "question.webm", content, audio.content_type or "audio/webm")
    return await _answer(connection, document_id, question, True)


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_voice(audio: UploadFile = File(...)):
    content = await audio.read()
    transcript = await AIService().transcribe(audio.filename or "question.webm", content, audio.content_type or "audio/webm")
    return TranscribeResponse(transcript=transcript)


@router.post("/evaluation/golden/{document_id}", response_model=EvaluationResponse)
async def run_golden_evaluation(document_id: int, connection: Connection = Depends(get_connection)):
    with connection.cursor() as cursor:
        cursor.execute("SELECT title FROM documents WHERE id = %s", (document_id,))
        document = cursor.fetchone()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    if document["title"] != SAMPLE_EVALUATION_TITLE:
        raise HTTPException(
            status_code=400,
            detail=(
                "The built-in golden-question evaluation is calibrated for the Aurora Operations Handbook sample. "
                "Custom books need their own expected questions, chapters, and answer terms."
            ),
        )

    retrieval_service = RetrievalService()
    ai = AIService()
    cases: list[EvaluationCaseOut] = []

    for golden in GOLDEN_QUESTIONS:
        retrieved = await retrieval_service.retrieve(connection, document_id, golden["question"])
        if not retrieved:
            cases.append(
                EvaluationCaseOut(
                    question=golden["question"],
                    expected_chapter=golden["expected_chapter"],
                    retrieved_chapters=[],
                    retrieval_pass=False,
                    keyword_hits=[],
                    answer_excerpt="No evidence was retrieved.",
                    passed=False,
                )
            )
            continue

        answer = await ai.answer(golden["question"], retrieved)
        retrieved_chapters = [row["chapter_number"] for row in retrieved[:3]]
        retrieval_pass = golden["expected_chapter"] in retrieved_chapters
        answer_lower = answer.lower()
        keyword_hits = [term for term in golden["expected_terms"] if term.lower() in answer_lower]
        keyword_pass = len(keyword_hits) >= max(1, min(2, len(golden["expected_terms"])))
        passed = retrieval_pass and keyword_pass

        cases.append(
            EvaluationCaseOut(
                question=golden["question"],
                expected_chapter=golden["expected_chapter"],
                retrieved_chapters=retrieved_chapters,
                retrieval_pass=retrieval_pass,
                keyword_hits=keyword_hits,
                answer_excerpt=_compact(answer),
                passed=passed,
            )
        )

    passed_count = sum(1 for case in cases if case.passed)
    return EvaluationResponse(document_id=document_id, passed=passed_count, total=len(cases), cases=cases)


async def _answer(connection: Connection, document_id: int, question: str, speak: bool) -> AskResponse:
    if not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    retrieved = await RetrievalService().retrieve(connection, document_id, question)
    ai = AIService()
    answer = await ai.answer(question, retrieved)
    audio_base64, audio_mime_type = await ai.synthesize(answer) if speak else (None, None)
    cited_source_numbers = _cited_source_numbers(answer, len(retrieved))
    evidence_rows = [retrieved[index - 1] for index in cited_source_numbers] if cited_source_numbers else retrieved[:3]

    citations = [
        Citation(
            chunk_id=row["id"],
            chapter_title=row["chapter_title"],
            chapter_number=row["chapter_number"],
            page_start=row["page_start"],
            page_end=row["page_end"],
            score=float(row["score"]),
            excerpt=row["excerpt"],
        )
        for row in evidence_rows
    ]

    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO qa_events (document_id, question, answer, citations) VALUES (%s, %s, %s, %s::jsonb)",
            (document_id, question, answer, "[" + ",".join(c.model_dump_json() for c in citations) + "]"),
        )
    connection.commit()

    return AskResponse(
        question=question,
        answer=answer,
        citations=citations,
        audio_base64=audio_base64,
        audio_mime_type=audio_mime_type,
    )


def _cited_source_numbers(answer: str, source_count: int) -> list[int]:
    seen: set[int] = set()
    ordered: list[int] = []
    for match in re.finditer(r"\[Source\s+(\d+)\]", answer, flags=re.IGNORECASE):
        source_number = int(match.group(1))
        if 1 <= source_number <= source_count and source_number not in seen:
            seen.add(source_number)
            ordered.append(source_number)
    return ordered


def _compact(text: str, limit: int = 220) -> str:
    cleaned = " ".join(text.split())
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 3] + "..."
