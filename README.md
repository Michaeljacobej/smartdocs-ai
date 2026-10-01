# SmartDocs AI

SmartDocs AI adalah prototype aplikasi untuk memproses dokumen transaksi secara otomatis, mulai dari upload file, OCR, klasifikasi tipe dokumen, ekstraksi data struktural, validasi, hingga pembuatan ringkasan menggunakan model AI lokal.

Tujuan utama aplikasi ini adalah membantu mengurangi pekerjaan manual pada dokumen seperti invoice, nota, atau bukti transaksi dengan pendekatan end-to-end yang sederhana namun cukup fungsional untuk prototype dan pengembangan lebih lanjut.

## Fitur utama

- Upload dokumen PDF atau gambar
- OCR otomatis menggunakan PaddleOCR
- Klasifikasi jenis dokumen
- Ekstraksi data seperti nomor dokumen, vendor, tanggal, total, pajak, dan mata uang
- Validasi logika data dan deteksi anomali
- Ringkasan AI berdasarkan teks OCR
- Workflow review/manual correction oleh pengguna
- Penyimpanan data di PostgreSQL

## Cara menjalankan aplikasi

### 1) Clone project dan siapkan environment

```bash
git clone <repo-url>
cd smartdocs-ai
copy .env.example .env
```

File `.env` berisi konfigurasi untuk backend dan frontend. Pastikan variabel utama sudah sesuai seperti:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/document_ai
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=qwen3
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### 2) Jalankan PostgreSQL

Rekomendasi paling mudah menggunakan Docker Compose:

```bash
docker compose up -d postgres
```

Ini akan menjalankan database PostgreSQL di port `5433` pada host (karena mapping `5433:5432` di Docker Compose).

### 3) Jalankan Ollama (opsional jika ingin gunakan LLM lokal)

Jika ingin menjalankan model AI lokal melalui Ollama:

```bash
docker compose --profile ollama up -d ollama
```

Lalu unduh model yang dibutuhkan, misalnya:

```bash
ollama pull qwen3
```

Atau gunakan model lain yang sudah diatur di `.env`.

### 4) Install dependency backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 5) Jalankan backend FastAPI

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend akan tersedia di:

- API: http://localhost:8000
- Health check: http://localhost:8000/health

### 6) Install dependency frontend

```bash
cd frontend
npm install
```

### 7) Jalankan frontend Next.js

```bash
cd frontend
npm run dev
```

Frontend akan tersedia di:

- http://localhost:3000

### 8) Akses aplikasi

Buka browser ke `http://localhost:3000` dan upload dokumen PDF atau gambar untuk diproses.

---

## Overview arsitektur / komponen

Aplikasi ini dibangun menggunakan pendekatan modular monolith, bukan microservices, karena kebutuhan prototype cepat dan pengelolaan yang lebih sederhana.

Komponen utama:

- Frontend: Next.js + React + TypeScript
- Backend: FastAPI + SQLAlchemy + Pydantic
- Database: PostgreSQL
- OCR engine: PaddleOCR
- LLM runtime: Ollama
- File storage: lokal di folder `backend/uploads`

Diagram alur proses:

```text
User / Browser
    -> Next.js Frontend
    -> FastAPI API
    -> DocumentService
        -> File validation
        -> OCRService
        -> ClassificationService
        -> ExtractionService
        -> ValidationService
        -> SummaryService
    -> PostgreSQL
    -> Ollama (LLM local)
```

Detail alur:

1. User mengunggah file PDF/gambar.
2. Backend menyimpan file ke `uploads` dan menyimpan metadata dokumen ke database.
3. Dokumen dimasukkan ke antrian background processing.
4. OCR dilakukan untuk menghasilkan raw text dari halaman dokumen.
5. Teks hasil OCR diklasifikasikan ke tipe dokumen tertentu.
6. Data ektraksi diproses dari teks OCR sesuai pola dokumen.
7. Hasil dievaluasi dengan validator dan confidence scoring.
8. Jika diperlukan, user dapat memperbaiki data yang diekstraksi.
9. Summary dibuat dari OCR text menggunakan model LLM lokal.

Struktur folder utama:

```text
smartdocs-ai/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── prompts/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── tests/
│   │   └── utils/
│   ├── alembic/
│   ├── requirements.txt
│   └── uploads/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── types/
├── docker-compose.yml
├── .env
├── .env.example
├── README.md
└── smartdocs-ai.postman_collection.json
```

---

## OCR & AI/LLM yang digunakan

### OCR

OCR yang dipakai adalah PaddleOCR.

Alasannya:

- cocok untuk dokumen cetak dan campuran teks serta tabel
- mendukung proses OCR pada PDF dan gambar
- dapat menghasilkan confidence score per baris teks
- relatif mudah diintegrasikan ke pipeline Python

Di backend, OCR dilakukan melalui `OCRService` yang:

- membaca PDF menggunakan PyMuPDF (`fitz`)
- melakukan ekstraksi teks yang bisa dibaca secara langsung jika tersedia
- jika teks tidak cukup, maka halaman PDF diubah menjadi gambar lalu diproses dengan PaddleOCR
- untuk file gambar, image diproses langsung dari array numpy/Pillow

### LLM / AI

Model AI dijalankan melalui Ollama sebagai runtime lokal.

Teknologi yang digunakan:

- `Ollama` untuk menjalankan model LLM secara lokal
- `httpx` untuk komunikasi ke endpoint Ollama
- abstraction `LLMProvider` sebagai lapisan umum agar business logic tidak tergantung langsung ke implementasi tertentu

Model yang umum dipakai untuk ekstraksi dan ringkasan adalah model dari keluarga Qwen, misalnya:

- `qwen3`
- `qwen2.5:0.5b` sebagai fallback / alternatif model ringan

Arsitektur LLM yang diterapkan:

- `ClassificationService` menggunakan LLM untuk menentukan tipe dokumen
- `ExtractionService` menggunakan prompt terstruktur untuk mengekstrak field penting dari OCR
- `SummaryService` menggunakan model LLM untuk membuat ringkasan singkat dari teks dokumen dalam bahasa Indonesia

Semua pemanggilan LLM dibungkus dalam adapter `OllamaProvider` agar nanti mudah mengganti backend model lain tanpa mengubah business service.

---

## Alasan pemilihan teknologi

### FastAPI

Dipilih karena:

- ringan dan cepat untuk API
- validasi data otomatis dengan Pydantic
- cocok untuk prototype produk dengan struktur backend yang terorganisir
- kompatibel dengan ekosistem Python dan SQLAlchemy

### Next.js + React + TypeScript

Dipilih karena:

- pengalaman UI yang cepat dan modern
- cocok untuk dashboard document processing
- struktur komponen yang mudah dikembangkan
- mudah diintegrasikan dengan backend API

### PostgreSQL

Dipilih karena:

- cocok untuk data relasional seperti dokumen, OCR result, ekstraksi, dan review
- mendukung transaksional data dengan integritas yang baik
- mudah dikelola melalui SQLAlchemy dan Alembic

### Ollama

Dipilih karena:

- memungkinkan menjalankan model LLM lokal tanpa bergantung pada layanan cloud
- cocok untuk prototipe dan lingkungan pengembangan yang lebih terkontrol
- lebih hemat biaya untuk penggunaan internal / eksperimen

### PaddleOCR

Dipilih karena:

- open-source dan cukup kuat untuk dokumen cetak
- cocok untuk tugas OCR document processing yang tidak terlalu kompleks
- dapat menghasilkan confidence score untuk evaluasi kualitas OCR

---

## Known limitations

Beberapa keterbatasan yang perlu diketahui saat ini:

- OCR masih sangat bergantung pada kualitas scan atau PDF. Dokumen buram, miring, atau banyak noise dapat menurunkan akurasi.
- Model LLM lokal mungkin lebih lambat dibanding layanan cloud dan terbatas oleh spesifikasi mesin.
- Saat ini pipeline lebih fokus pada dokumen transaksi tertentu, bukan seluruh jenis dokumen secara umum.
- Validasi masih relatif rule-based dan belum sepenuhnya dapat mengenali semua pola anomali yang kompleks.
- Antrian processing bersifat in-memory, sehingga belum sepenuhnya siap untuk skala produksi multi-worker atau failover.
- Belum ada autentikasi/otorisasi user yang kuat untuk akses aplikasi.
- Penyimpanan file saat ini masih lokal, belum menggunakan object storage seperti S3 atau GCS.

---

## Perbaikan yang akan dilakukan jika aplikasi dikembangkan lebih lanjut

Beberapa area pengembangan yang direncanakan:

1. Skalabilitas
   - mengganti antrian in-memory dengan Celery/RQ atau message broker
   - menambahkan worker yang lebih banyak dan monitoring job queue

2. Kualitas OCR dan ekstraksi
   - menambahkan model OCR yang lebih kuat untuk dokumen low-quality
   - memperbaiki prompt dan pola extraction untuk jenis dokumen yang lebih beragam
   - menambahkan eksekusi batch dan proses multi-page yang lebih optimal

3. Kualitas AI
   - membandingkan beberapa model LLM untuk performa terbaik per tugas
   - menambahkan fallback model yang lebih robust
   - memperbaiki prompt untuk output JSON yang lebih konsisten

4. UX dan review workflow
   - menambahkan halaman review yang lebih kaya untuk koreksi data manual
   - menampilkan confidence score per field secara lebih visual
   - menambahkan history perubahan data dan audit log

5. Produksi-ready platform
   - menambahkan autentikasi dan otorisasi
   - menjalankan backend dan frontend di environment terpisah / deployment pipeline
   - menambahkan monitoring, logging terpusat, dan alerting
   - migrasi storage file ke object storage

6. Integrasi bisnis
   - integrasi dengan ERP atau sistem akuntansi
   - export data ke format Excel/CSV
   - dukungan multi-tenant dan RBAC

---

## API utama

Endpoint yang sudah tersedia di backend:

- `POST /documents` — upload dokumen
- `GET /documents` — daftar dokumen
- `GET /documents/{id}` — detail dokumen
- `DELETE /documents/{id}` — hapus dokumen
- `PUT /documents/{id}/extracted-data` — koreksi data hasil ekstraksi
- `POST /documents/{id}/summary` — generate ringkasan dokumen
- `GET /documents/{id}/file` — ambil file asli dokumen
- `GET /health` — health check API

---

## Catatan tambahan

Proyek ini dibuat sebagai solusi prototype dengan fokus pada validasi konsep: menggabungkan OCR, ekstraksi data, validasi, dan ringkasan AI dalam satu pipeline yang dapat dijalankan secara lokal. Karena itu, arsitektur yang dipilih tetap sederhana, mudah dipahami, dan cepat dikembangkan sebelum masuk ke tahap produksi.

Jika Anda ingin lanjut mengembangkan aplikasi ini ke lingkungan enterprise, langkah berikutnya yang paling penting adalah memperkuat pipeline observability, skalabilitas worker, dan kualitas model untuk berbagai jenis dokumen.

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
