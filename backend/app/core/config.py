from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://voice_rag:voice_rag@localhost:5433/voice_rag"
    api_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,https://pdf-analyzer-web.onrender.com"

    gemini_api_key: str = ""
    gemini_answer_model: str = "gemini-3.1-flash-lite"
    gemini_transcription_model: str = "gemini-3.1-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_tts_model: str = "gemini-3.1-flash-tts-preview"
    gemini_tts_voice: str = "Kore"

    deepgram_api_key: str = ""
    deepgram_model: str = "nova-3"
    deepgram_language: str = "en"
    deepgram_keyterms: str = "incident readiness,hybrid search,reranking,retrieval quality,answer traceability,signal quality,governance controls,executive reporting"

    embedding_dimensions: int = 384
    retrieval_candidate_count: int = 28
    retrieval_context_count: int = 6
    answer_max_output_tokens: int = 650
    auto_seed_sample_book: bool = False
    sample_book_path: str = "../sample_data/aurora_operations_handbook.pdf"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
