from pathlib import Path

import psycopg

from app.services.embedding_service import EmbeddingService, vector_literal
from app.services.pdf_service import extract_pdf


class IndexingService:
    def __init__(self) -> None:
        self.embedding_service = EmbeddingService()

    async def index_pdf(self, connection: psycopg.Connection, path: Path, filename: str) -> dict:
        extracted = extract_pdf(path)
        title = Path(filename).stem.replace("_", " ").replace("-", " ").title()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO documents (filename, title, chapter_count, page_count, status)
                VALUES (%s, %s, %s, %s, 'indexing')
                RETURNING id, filename, title, chapter_count, page_count, status
                """,
                (filename, title, extracted["chapter_count"], extracted["page_count"]),
            )
            document = dict(cursor.fetchone())

        for chunk in extracted["chunks"]:
            embedding = await self.embedding_service.embed(f"{chunk.chapter_title}\n{chunk.content}")
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO chunks
                    (document_id, chapter_title, chapter_number, page_start, page_end, chunk_index, content, token_estimate, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
                    """,
                    (
                        document["id"],
                        chunk.chapter_title,
                        chunk.chapter_number,
                        chunk.page_start,
                        chunk.page_end,
                        chunk.chunk_index,
                        chunk.content,
                        chunk.token_estimate,
                        vector_literal(embedding),
                    ),
                )

        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE documents SET status = 'indexed' WHERE id = %s RETURNING id, filename, title, chapter_count, page_count, status",
                (document["id"],),
            )
            indexed = dict(cursor.fetchone())
        connection.commit()
        return indexed
