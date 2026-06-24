from __future__ import annotations

import re
from dataclasses import dataclass


CHAPTER_RE = re.compile(r"^\s*chapter\s+(\d+|[ivxlcdm]+)\b[:.\-\s]*(.*)$", re.IGNORECASE)
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass
class PageText:
    page_number: int
    text: str


@dataclass
class Chapter:
    number: int
    title: str
    pages: list[PageText]


@dataclass
class Chunk:
    chapter_number: int
    chapter_title: str
    page_start: int
    page_end: int
    chunk_index: int
    content: str
    token_estimate: int


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_chapters(pages: list[PageText]) -> list[Chapter]:
    chapters: list[Chapter] = []
    current: Chapter | None = None
    synthetic_number = 0

    for page in pages:
        text = normalize_text(page.text)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        heading = next((line for line in lines[:8] if CHAPTER_RE.match(line)), "")

        if heading:
            match = CHAPTER_RE.match(heading)
            raw_number = match.group(1).strip() if match else str(synthetic_number + 1)
            synthetic_number = int(raw_number) if raw_number.isdigit() else synthetic_number + 1
            suffix = match.group(2).strip() if match else ""
            title = heading if not suffix else f"Chapter {synthetic_number}: {suffix}"
            current = Chapter(number=synthetic_number, title=title, pages=[])
            chapters.append(current)
        elif current is None:
            synthetic_number += 1
            current = Chapter(number=synthetic_number, title="Front Matter", pages=[])
            chapters.append(current)

        current.pages.append(PageText(page.page_number, text))

    return chapters


def chapter_aware_chunks(chapters: list[Chapter], target_tokens: int = 360, overlap_sentences: int = 2) -> list[Chunk]:
    chunks: list[Chunk] = []
    chunk_index = 0

    for chapter in chapters:
        if chapter.title == "Front Matter":
            continue

        sentence_records: list[tuple[str, int]] = []
        for page in chapter.pages:
            paragraphs = [p.strip() for p in page.text.split("\n\n") if p.strip()]
            for paragraph in paragraphs:
                for sentence in SENTENCE_RE.split(paragraph):
                    sentence = sentence.strip()
                    if sentence:
                        sentence_records.append((sentence, page.page_number))

        start = 0
        while start < len(sentence_records):
            token_count = 0
            end = start
            while end < len(sentence_records) and token_count < target_tokens:
                token_count += estimate_tokens(sentence_records[end][0])
                end += 1

            selected = sentence_records[start:end]
            content = " ".join(sentence for sentence, _ in selected)
            if content:
                pages = [page for _, page in selected]
                chunks.append(
                    Chunk(
                        chapter_number=chapter.number,
                        chapter_title=chapter.title,
                        page_start=min(pages),
                        page_end=max(pages),
                        chunk_index=chunk_index,
                        content=content,
                        token_estimate=estimate_tokens(content),
                    )
                )
                chunk_index += 1

            if end >= len(sentence_records):
                break
            start = max(end - overlap_sentences, start + 1)

    return chunks


def estimate_tokens(text: str) -> int:
    return max(1, len(re.findall(r"\w+|[^\w\s]", text)) * 3 // 4)


def keywords(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text)]
