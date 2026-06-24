import asyncio
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.db.database import init_db  # noqa: E402
from app.services.indexing_service import IndexingService  # noqa: E402


SAMPLE_PDF = ROOT / "sample_data" / "aurora_operations_handbook.pdf"


async def main() -> None:
    if not SAMPLE_PDF.exists():
        raise SystemExit(f"Sample PDF not found: {SAMPLE_PDF}")

    init_db()
    settings = get_settings()
    with psycopg.connect(settings.database_url, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM documents
                WHERE lower(title) = 'aurora operations handbook'
                   OR filename = 'aurora_operations_handbook.pdf'
                """
            )
        connection.commit()

        document = await IndexingService().index_pdf(connection, SAMPLE_PDF, SAMPLE_PDF.name)

    print(
        "Indexed cleaned sample:",
        f"id={document['id']}",
        f"title={document['title']}",
        f"sections={document['chapter_count']}",
        f"pages={document['page_count']}",
    )


if __name__ == "__main__":
    asyncio.run(main())
