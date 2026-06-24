from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: int
    filename: str
    title: str
    chapter_count: int
    page_count: int
    status: str


class Citation(BaseModel):
    chunk_id: int
    chapter_title: str
    chapter_number: int
    page_start: int
    page_end: int
    score: float
    excerpt: str


class AskTextRequest(BaseModel):
    document_id: int
    question: str
    speak: bool = True


class TranscribeResponse(BaseModel):
    transcript: str


class AskResponse(BaseModel):
    question: str
    answer: str
    citations: list[Citation]
    audio_base64: str | None = None
    audio_mime_type: str | None = None


class EvaluationCaseOut(BaseModel):
    question: str
    expected_chapter: int
    retrieved_chapters: list[int]
    retrieval_pass: bool
    keyword_hits: list[str]
    answer_excerpt: str
    passed: bool


class EvaluationResponse(BaseModel):
    document_id: int
    passed: int
    total: int
    cases: list[EvaluationCaseOut]


class HealthResponse(BaseModel):
    status: str
    database: str
    ai_provider: str
