# AI Document Processing Portal

A 1-day prototype for end-to-end transaction document processing:

1. Upload document
2. OCR extraction (PaddleOCR)
3. Classification
4. Structured extraction (rule + LLM fallback)
5. Validation/anomaly checks
6. AI summary generation (Ollama + Qwen3)
7. Human correction workflow
8. Persist all results in PostgreSQL

## Overview

This project is implemented as a modular monolith:

- Next.js frontend (dashboard + document detail)
- FastAPI backend (API + processing services)
- PostgreSQL (document, OCR, extraction, summary data)
- Ollama (local model serving)

No unnecessary microservices are introduced.

## Architecture

User  
-> Next.js Frontend  
-> FastAPI Backend  
-> Document Processing Service  
-> PaddleOCR  
-> Raw OCR Result  
-> Classification  
-> Extraction  
-> Validation  
-> Structured Data (PostgreSQL)  
-> Summary Service  
-> LLM Provider Abstraction  
-> Ollama + Qwen3  
-> Summary (PostgreSQL)

## Tech Stack

Backend:
- Python 3.12+
- FastAPI
- SQLAlchemy
- Pydantic v2
- Alembic
- PostgreSQL
- Uvicorn

Frontend:
- Next.js 15
- React 19
- TypeScript
- Tailwind CSS

OCR:
- PaddleOCR

LLM:
- Ollama + Qwen3

## Project Structure

```text
.
├── backend
│   ├── alembic
│   ├── app
│   │   ├── api
│   │   ├── core
│   │   ├── db
│   │   ├── prompts
│   │   ├── schemas
│   │   ├── services
│   │   └── utils
│   ├── tests
│   ├── requirements.txt
│   └── .env.example
├── frontend
│   ├── app
│   ├── components
│   ├── lib
│   ├── types
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

## Database Schema

Tables:
- `documents`
- `ocr_results`
- `extracted_data`
- `summaries`

Highlights:
- UUID primary keys
- Foreign key constraints with cascade delete
- Timestamps (`created_at`, `updated_at`)
- Indexes on status, date, type, common search keys
- Original and corrected extracted values are stored separately

## OCR Approach

PaddleOCR is used because it works well for mixed printed document layouts and supports confidence scoring. OCR results are stored as raw text plus metadata (`processing_status`, `processing_time_ms`, `error_message`) and line-level confidence payload in `confidence_data`.

## Extraction Approach

1. Rule-based extraction first for reliable patterns.
2. LLM fallback for missing/complex fields.
3. Strict Pydantic validation (`ExtractedFields`).
4. Invalid/malformed LLM JSON is not accepted silently.

Fields:
- document_number
- vendor
- document_date
- total_amount
- tax_amount
- currency

Normalization:
- Date to `YYYY-MM-DD`
- Amount to numeric
- Currency to uppercase code

## Validation Strategy

`ValidationService` performs:
- schema and date validation
- currency checks
- amount checks
- consistency checks (e.g., tax > total anomaly)

Anomalies are persisted in `confidence_data.anomalies` and do not block persistence of the document.

## LLM Strategy

An abstraction layer is used:

- `LLMProvider` interface (`generate_text`)
- `OllamaProvider` implementation (`OLLAMA_BASE_URL`, `LLM_MODEL`)

Business services depend on `LLMProvider`, not directly on Ollama.

## Prompt Design

Dedicated prompts:
- extraction prompt: strict JSON, no hallucination, null when unknown
- summary prompt: summarize only from persisted OCR text in Indonesian
- classification prompt hint for fallback

## Human Correction

`PUT /documents/{id}/extracted-data` stores corrected values in `*_corrected` columns while preserving `*_original` values for traceability.

## API Documentation

Implemented endpoints:
- `POST /documents`
- `GET /documents`
- `GET /documents/{id}`
- `DELETE /documents/{id}`
- `PUT /documents/{id}/extracted-data`
- `POST /documents/{id}/summary`
- `GET /documents/{id}/file`

Error payload format:

```json
{
  "error": {
    "code": "DOCUMENT_NOT_FOUND",
    "message": "Document not found"
  }
}
```

## Environment Variables

Root `.env` (example in `.env.example`):

- `DATABASE_URL`
- `OLLAMA_BASE_URL`
- `LLM_MODEL`
- `LLM_SUMMARY_MODEL`
- `LLM_SUMMARY_FALLBACK_MODEL`
- `OLLAMA_TIMEOUT_SECONDS`
- `OLLAMA_SUMMARY_TIMEOUT_SECONDS`
- `OLLAMA_KEEP_ALIVE`
- `OLLAMA_THINK`
- `OLLAMA_RETRY_ATTEMPTS`
- `OLLAMA_RETRY_BACKOFF_SECONDS`
- `OLLAMA_NUM_PREDICT`
- `OLLAMA_NUM_CTX`
- `OLLAMA_TEMPERATURE`
- `OLLAMA_SUMMARY_NUM_PREDICT`
- `OLLAMA_SUMMARY_NUM_CTX`
- `OLLAMA_SUMMARY_TEMPERATURE`
- `SUMMARY_MAX_OCR_CHARS`
- `UPLOAD_DIR`
- `MAX_FILE_SIZE_MB`
- `APP_ENV`
- `DEBUG`
- `NEXT_PUBLIC_API_BASE_URL`

## Installation

### 1) Prepare environment files

- Copy `.env.example` to `.env`
- Copy `frontend/.env.example` to `frontend/.env.local`
- Optionally copy `backend/.env.example` to `backend/.env`

### 2) Python/backend dependencies

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3) Frontend dependencies

```bash
cd frontend
npm install
```

## Running PostgreSQL

Option A (Docker Compose recommended):

```bash
docker compose up -d postgres
```

Option B (local PostgreSQL):
- Ensure DB exists and `DATABASE_URL` points to it.

## Running Ollama

Option A (local installation):
- Install Ollama from official docs.
- Start Ollama service.

Option B (Docker Compose optional profile):

```bash
docker compose --profile ollama up -d ollama
```

## Pulling Qwen3

```bash
ollama pull qwen3
```

If you use another model, set `LLM_MODEL` accordingly.

## Database Migration

```bash
cd backend
alembic upgrade head
```

## Running Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

## Running Frontend

```bash
cd frontend
npm run dev
```

Open `http://localhost:3000`.

## Demo Flow

1. Upload invoice (PDF/JPG/PNG)
2. Status switches to `PROCESSING`
3. PaddleOCR extracts raw text
4. Classification runs
5. Structured extraction runs
6. Validation runs
7. OCR + extraction persisted
8. Generate summary from stored OCR text
9. Summary persisted
10. Review document detail page
11. Correct one extracted field
12. Corrected value stored while original remains
13. Dashboard reflects latest status/data

## Testing

Run:

```bash
cd backend
pytest
```

Tests include:
- unsupported file type
- document not found
- extraction schema validation
- corrected extraction traceability
- summary service generation
- basic upload endpoint behavior

External OCR/LLM dependencies are mocked in tests.

## Error Handling

- 400 unsupported file
- 404 document not found
- 422 request validation error
- 500 unexpected server error
- 503 OCR/LLM unavailable

No stack traces are exposed to clients.

## Security Considerations

- environment variables for runtime settings
- no API keys or secrets in source
- strict file extension and MIME checks
- file size validation
- generated safe server-side filenames
- no direct use of original filename as path
- LLM JSON output validation
- no unsafe HTML rendering

## Known Limitations

- Prototype is not production-ready.
- Uses background tasks in-process (not distributed workers).
- Local Ollama performance depends on hardware.
- OCR quality depends on input document quality.
- LLM output is validated but still requires human review.
- Authentication is intentionally omitted for this 1-day scope.

## Trade-offs

- Chosen modular monolith for speed and maintainability in a test setting.
- Background task processing keeps architecture simple, but lacks advanced retry/queue semantics.
- Rule-first extraction improves determinism; LLM fallback improves coverage at cost of variability.

## Future Improvements

- authentication/authorization
- object storage integration
- async job queue and retry policies
- richer OCR confidence visualization
- advanced anomaly detection
- full-text search and filtered queries
- document versioning and audit log
- observability and monitoring
- API rate limiting
