# Voice RAG Book QA

A polished full-stack assignment project for voice-based question answering over an uploaded PDF book.

## Pipeline

1. ASR: browser microphone audio is sent to FastAPI and transcribed with Deepgram Nova-3, with Gemini audio understanding as a fallback.
2. RAG: the uploaded PDF is parsed into detected sections, section-aware chunks are indexed, hybrid retrieval combines pgvector dense search with PostgreSQL full-text search, and a lightweight reranker improves the final context.
3. LLM: Gemini generates a grounded answer with source citations from the retrieved chunks.
4. TTS: Gemini text-to-speech converts the answer to speech and the browser plays the returned audio.

The backend includes local fallbacks for embeddings and answer/TTS placeholders so the project remains demoable without keys, but a Gemini API key is recommended for the graded pipeline.

## Tech Stack

- Frontend: Vite, React, TypeScript, CSS
- API: FastAPI, Python
- Database: Docker PostgreSQL with pgvector
- PDF parsing: pypdf
- AI APIs: Deepgram for ASR, Gemini for embeddings, answer generation, and speech synthesis

## Quick Start

```bash
cd voice-rag-book-qa
cp .env.example .env
docker compose up -d db

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

cd ../frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Deploy on Render

This repo includes `render.yaml` so the app can be deployed as a Render Blueprint:

- `pdf-analyzer-web`: Vite/React static site
- `pdf-analyzer-api`: FastAPI backend
- `pdf-analyzer-db`: PostgreSQL database with `pgvector`

Deployment steps:

1. Push this repository to GitHub.
2. In Render, create a new Blueprint from the GitHub repository.
3. Add these secret environment variables when Render asks:
   - `GEMINI_API_KEY`
   - `DEEPGRAM_API_KEY`
4. Deploy the Blueprint.
5. Open the frontend URL, upload `sample_data/aurora_operations_handbook.pdf`, then ask a question.

The blueprint assumes these Render service URLs:

- Frontend: `https://pdf-analyzer-web.onrender.com`
- Backend: `https://pdf-analyzer-api.onrender.com/api`

If Render assigns different service URLs, update:

- Backend `API_CORS_ORIGINS`
- Frontend `VITE_API_BASE`

If your Render account does not offer a free PostgreSQL plan, use Render's smallest PostgreSQL plan or connect the backend to an external PostgreSQL database that supports `pgvector`.

## API Keys

Set `GEMINI_API_KEY` in `.env` for the full ASR -> RAG -> LLM -> TTS path.

Set `DEEPGRAM_API_KEY` in `.env` for higher-quality speech-to-text. Deepgram is used only for ASR; Gemini still handles RAG embeddings, answer generation, and TTS.

The app is designed for free-tier testing by keeping calls small:

- Uploading the sample book embeds a small set of section-aware chunks.
- Each question sends one query embedding, about six retrieved chunks to the LLM, and one short TTS request.
- The entire PDF is never sent to Gemini during question answering.

Verify your Gemini key without printing it:

```bash
cd voice-rag-book-qa
set -a && source .env && set +a
backend/.venv/bin/python scripts/check_gemini.py
```

Expected checks: embedding, answer generation, TTS, and transcription all return `ok`.

Run the golden-question RAG evaluation:

```bash
cd voice-rag-book-qa
set -a && source .env && set +a
backend/.venv/bin/python scripts/evaluate_answers.py
```

The webpage also includes a sample-only `Sample evaluation` scorecard for the included Aurora Operations Handbook. That scorecard is intentionally calibrated to Aurora's expected chapters and answer terms. Custom uploaded books still support the full voice RAG workflow, but they need their own golden questions and expected facts for automated quality evaluation.

For a cheaper retrieval-only check:

```bash
backend/.venv/bin/python scripts/evaluate_answers.py --retrieval-only
```

## Sample PDF

Generate the required 10-chapter sample book:

```bash
cd voice-rag-book-qa
backend/.venv/bin/python scripts/generate_sample_book.py
```

The generated file is written to `sample_data/aurora_operations_handbook.pdf`.

The sample book contains 10 chapters with chapter-specific content for testing retrieval diversity. To replace an older indexed Aurora sample with the cleaned version:

```bash
backend/.venv/bin/python scripts/reindex_sample_book.py
```

## Demo Questions

Type these into the question box for richer text answers:

- Why does the handbook recommend hybrid search and reranking?
- How should the team handle incident readiness?
- What governance controls should be in place for policy changes?
- How should answer quality be evaluated?
- What should executive reporting include?

Try these shorter questions through the microphone:

- Explain hybrid search.
- What is incident readiness?
- How should voice playback work?

## Retrieval Design

The assignment warns against naive fixed-size chunking. This implementation uses:

- Chapter detection from headings
- Paragraph and sentence-aware chunking with overlap
- Chapter/page metadata stored with every chunk
- Hybrid retrieval: dense vector similarity plus PostgreSQL `tsvector` keyword ranking
- Query embedding task types plus lightweight reranking
- Citations in answers so users can inspect grounding

See `docs/architecture.md` for the detailed acceptance strategy.
