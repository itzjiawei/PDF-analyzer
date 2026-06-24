from app.services.text_processing import PageText, chapter_aware_chunks, detect_chapters


def test_detects_chapters_and_chunks_with_metadata():
    pages = [
        PageText(1, "Chapter 1: Reliability\n\nSystems need clear signals. Teams review latency. Incidents need owners."),
        PageText(2, "More detail. Recovery plans are rehearsed. Reviews produce decisions."),
        PageText(3, "Chapter 2: Governance\n\nPolicy defines ownership. Audits verify evidence."),
    ]

    chapters = detect_chapters(pages)
    chunks = chapter_aware_chunks(chapters, target_tokens=18, overlap_sentences=1)

    assert len(chapters) == 2
    assert chapters[0].title == "Chapter 1: Reliability"
    assert chunks[0].chapter_number == 1
    assert chunks[0].page_start == 1
    assert chunks[-1].chapter_number == 2
