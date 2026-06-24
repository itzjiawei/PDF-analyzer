from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from app.core.config import get_settings
from app.services.indexing_service import IndexingService

SAMPLE_TITLE = "Aurora Operations Handbook"


async def seed_sample_book() -> None:
    settings = get_settings()
    if not settings.auto_seed_sample_book:
        return

    sample_path = Path(settings.sample_book_path)
    if not sample_path.exists():
        print(f"Sample seed skipped: {sample_path} does not exist.")
        return

    with psycopg.connect(settings.database_url, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM documents WHERE title = %s LIMIT 1", (SAMPLE_TITLE,))
            existing = cursor.fetchone()

        if existing:
            return

        await IndexingService().index_pdf(connection, sample_path, sample_path.name)
        print(f"Seeded sample book: {SAMPLE_TITLE}")
