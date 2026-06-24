from pathlib import Path

from pypdf import PdfReader

from app.services.text_processing import PageText, chapter_aware_chunks, detect_chapters, normalize_text


def extract_pdf(path: Path):
    reader = PdfReader(str(path))
    pages = [
        PageText(page_number=index + 1, text=normalize_text(page.extract_text() or ""))
        for index, page in enumerate(reader.pages)
    ]
    chapters = detect_chapters(pages)
    chunks = chapter_aware_chunks(chapters)
    title = path.stem.replace("_", " ").replace("-", " ").title()
    return {
        "title": title,
        "page_count": len(pages),
        "chapter_count": len([c for c in chapters if c.title != "Front Matter"]),
        "chunks": chunks,
    }
