from app.services.embedding_service import EmbeddingService


def test_hash_embedding_has_expected_dimensions():
    service = EmbeddingService()
    vector = service._embed_hashing("chapter reliability latency incident response")

    assert len(vector) == service.settings.embedding_dimensions
    assert any(value != 0 for value in vector)
