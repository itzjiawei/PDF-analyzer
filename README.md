# PDF Analyzer: Voice RAG Book QA

A full-stack web application that lets users upload a PDF book, ask questions through the microphone or text input, and receive grounded answers with citations and browser-playable speech.

## Live Demo

Try the deployed app here:

[https://pdf-analyzer-web.onrender.com/](https://pdf-analyzer-web.onrender.com/)

The deployed demo is preloaded with the sample `Aurora Operations Handbook`. You can also upload another PDF book and ask questions against that uploaded source.

## Core Pipeline

1. **ASR**: Browser microphone audio is sent to FastAPI and transcribed with Deepgram Nova-3, with Gemini audio understanding as a fallback.
2. **RAG**: Uploaded PDFs are parsed into detected sections, indexed as section-aware chunks, retrieved with hybrid dense and keyword search, then reranked for relevance.
3. **LLM**: Gemini generates grounded answers from the retrieved context and includes source citations.
4. **TTS**: Gemini text-to-speech converts the generated answer into browser-playable audio.

## Tech Stack

- Frontend: Vite, React, TypeScript, CSS
- API: FastAPI, Python
- Database: PostgreSQL with `pgvector`
- PDF parsing: `pypdf`
- AI APIs: Deepgram for ASR; Gemini for embeddings, answer generation, and TTS
- Deployment: Render static site, Render FastAPI service, Render PostgreSQL

## Key Features

- Upload and reuse PDF books from the Book Library
- Ask questions by microphone or text
- Review/edit recognized speech before sending
- View grounded answers with cited evidence
- Listen to answer playback with read-along highlighting
- Inspect retrieved evidence in a scrollable panel
- Run a sample-only quality evaluation for the Aurora handbook

## Local Setup

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

## Environment Variables

Set these in `.env` for local development:

```bash
GEMINI_API_KEY=
DEEPGRAM_API_KEY=
DATABASE_URL=postgresql://voice_rag:voice_rag@localhost:5433/voice_rag
```

Gemini is used for embeddings, answer generation, and TTS. Deepgram is used for higher-quality speech-to-text.

The app keeps API usage small by embedding section-aware chunks, retrieving only the most relevant context, and sending short answer/TTS requests.

## Render Deployment

This repository includes `render.yaml` for Blueprint deployment:

- `pdf-analyzer-web`: Vite/React static site
- `pdf-analyzer-api`: FastAPI backend
- `pdf-analyzer-db`: PostgreSQL database with `pgvector`

Current deployed URLs:

- Frontend: [https://pdf-analyzer-web.onrender.com/](https://pdf-analyzer-web.onrender.com/)
- Backend API: `https://pdf-analyzer-api-3qy8.onrender.com/api`

Render environment variables:

- `GEMINI_API_KEY`
- `DEEPGRAM_API_KEY`
- `VITE_API_BASE=https://pdf-analyzer-api-3qy8.onrender.com/api`
- `AUTO_SEED_SAMPLE_BOOK=true`

On Render, the Aurora sample book is indexed into the deployed database on first backend startup. Locally, `AUTO_SEED_SAMPLE_BOOK` defaults to `false`.

## Sample PDF

The required 10-chapter sample book is included at:

```text
sample_data/aurora_operations_handbook.pdf
```

To regenerate it:

```bash
cd voice-rag-book-qa
backend/.venv/bin/python scripts/generate_sample_book.py
```

To reindex the sample into the local database:

```bash
backend/.venv/bin/python scripts/reindex_sample_book.py
```

## Demo Questions

Good text questions:

- Why does the handbook recommend hybrid search and reranking?
- How should the team handle incident readiness?
- What governance controls should be in place for policy changes?
- How should answer quality be evaluated?
- What should executive reporting include?

Short microphone questions:

- Explain hybrid search.
- What is incident readiness?
- How should voice playback work?

## Testing And Evaluation

Backend tests:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest
```

Golden-question evaluation for the Aurora sample:

```bash
cd voice-rag-book-qa
set -a && source .env && set +a
backend/.venv/bin/python scripts/evaluate_answers.py
```

The webpage also exposes the Aurora-only `Sample evaluation` scorecard when the Aurora handbook is selected. Custom uploaded books support the full voice RAG workflow, but automated quality scoring requires a book-specific golden question set.

## Documentation

See [docs/architecture.md](docs/architecture.md) for:

- Architecture and data flow
- Retrieval design decisions
- AI-assisted workflow notes
- Testing and acceptance strategy
- Answer-quality evaluation approach
