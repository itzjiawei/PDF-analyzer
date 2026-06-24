from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.db.database import init_db
from app.db.seed import seed_sample_book


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Voice RAG Book QA", version="1.0.0")
    app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://pdf-analyzer-web.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    )
    app.include_router(router, prefix="/api")

    @app.on_event("startup")
    async def startup() -> None:
        init_db()
        await seed_sample_book()

    return app


app = create_app()
