<div align="center">

# SiArsip: Sistem Manajemen Arsip Digital Pasien Terenkripsi

*Encrypted Patient Archive · FastAPI + Next.js · AES-GCM / DES-CBC / RC4 · Steganografi Citra Medis*

<br />

<p>
  <img src="https://img.shields.io/badge/AES--256-GCM-2E7D32?style=flat-square" alt="AES-256-GCM" />
  <img src="https://img.shields.io/badge/DES-CBC%20%2B%20HMAC-F9A825?style=flat-square" alt="DES-CBC + HMAC" />
  <img src="https://img.shields.io/badge/RC4-drop3072%20%2B%20HMAC-C62828?style=flat-square" alt="RC4 drop3072 + HMAC" />
  <img src="https://img.shields.io/badge/Compliance-UU%20PDP%2027%2F2022-6A1B9A?style=flat-square" alt="UU PDP 27/2022" />
</p>

Arsip dokumentasi pasien (rontgen, foto luka, scan KTP, dokumen, dan video) yang dienkripsi sebelum disimpan, hanya dapat diakses kembali secara utuh oleh pemilik yang berwenang, serta dilengkapi identitas tersembunyi di dalam citra medis.

[Fitur](#fitur) · [Arsitektur](#arsitektur) · [Kriptografi](#desain-kriptografi) · [Instalasi](#instalasi) · [Benchmark](#evaluasi-cipher) · [Tim](#tim)

</div>

---

## Daftar Isi

- [Tentang Proyek](#tentang-proyek)
- [Fitur Utama](#fitur-utama)
- [Arsitektur Sistem](#arsitektur-sistem)
- [Model Keamanan](#model-keamanan)
- [Referensi API](#referensi-api)
- [Teknologi](#teknologi)
- [Struktur Repositori](#struktur-repositori)
- [Memulai (Quick Start)](#memulai-quick-start)
- [Konfigurasi Environment](#konfigurasi-environment)
- [Database & Migrasi](#database--migrasi)
- [Pengujian](#pengujian)
- [CI/CD & Deployment](#cicd--deployment)
- [Konvensi Tim](#konvensi-tim)
- [Dokumentasi Lanjutan](#dokumentasi-lanjutan)
- [Pemecahan Masalah](#pemecahan-masalah)
- [Peta Jalan](#peta-jalan)
- [Lisensi](#lisensi)

---

## Tentang Proyek

**SiArsip** adalah platform arsip kesehatan digital yang dirancang dengan prinsip *privacy by design*: seluruh data identitas pasien maupun berkas medis disimpan dalam keadaan terenkripsi, baik di database maupun di object storage. Setiap orang hanya dapat mengakses data miliknya sendiri — kepemilikan ditegakkan pada level *query* SQL, bukan pada pemeriksaan pasca-fetch.

Proyek ini dikembangkan sebagai tugas mata kuliah **Keamanan Informasi** dengan fokus pada **enkripsi simetris** dan penerapan praktis kontrol keamanan pada sistem informasi nyata:

| Aspek | Implementasi |
| :--- | :--- |
| **Kerahasiaan (Confidentiality)** | AES-256-GCM, DES-CBC, RC4 (per berkas, key acak per objek) |
| **Keutuhan (Integrity)** | AEAD tag / HMAC-SHA256 *encrypt-then-MAC* + verifikasi SHA-256 plaintext |
| **Autentikasi (Authentication)** | JWT bearer token, kata sandi di-hash dengan Argon2 |
| **Otorisasi (Authorization)** | *Owner-scoped queries* di lapisan repository (anti-IDOR) |
| **Kepatuhan Privasi** | Klasifikasi data berdasarkan **UU PDP Pasal 4** (umum vs. spesifik), masking NIK |
| **Perlindungan Data Bersama** | Steganografi LSB pada citra klinis untuk menyembunyikan identitas pasien |

---

## Fitur Utama

### Manajemen Akun
- Registrasi dengan validasi email, nama unik, dan panjang kata sandi.
- Login berbasis email → menerbitkan **JWT** (HS256, masa berlaku 60 menit) beserta informasi pengguna.
- Password disimpan sebagai hash **Argon2** (`pwdlib.recommended()`).

### Manajemen Pasien
- CRUD rekam pasien dengan **enkripsi menyeluruh**: nama, MRN, NIK, tanggal lahir, dan diagnosis tidak pernah tersimpan dalam bentuk plaintext.
- Daftar pasien menampilkan **NIK ter-mask** (`3201********0001`) dan **menyembunyikan diagnosis**.
- Validasi domain: NIK 16 digit, MRN `[A-Za-z0-9/-]`, tanggal lahir tidak boleh di masa depan.
- Hapus pasien otomatis menghapus seluruh berkas terkait (cascade) termasuk objek di storage.

### Manajemen Berkas Medis
Empat kategori berkas dengan aturan MIME & klasifikasi PDP yang berbeda:

| Kategori | Format yang diizinkan | Klasifikasi PDP |
| :--- | :--- | :--- |
| `identity_scan` | JPEG, PNG, PDF (KTP, BPJS) | Umum |
| `office_document` | PDF, DOCX, XLSX (consent, rujukan) | Spesifik |
| `video` | MP4 (perawatan luka, USG) | Spesifik |
| `clinical_image` | JPEG, PNG (rontgen, foto luka) — **dapat dibagikan** | Spesifik |

- **Validasi berlapis**: deteksi MIME berdasarkan *magic bytes* + validasi struktural nyata (parser PIL untuk gambar, marker `%%EOF`/catalog untuk PDF, box `ftyp`/`moov` untuk MP4, paket OOXML untuk DOCX/XLSX).
- **Anti-penyamaran executable**: menolak berkas dengan signature `MZ`, `ELF`, Mach-O, atau shebang, termasuk *header grafting* (`%PDF-...MZ...`).
- Batas ukuran unggah **100 MiB**, dibaca secara streaming per chunk.
- Unduh respons menyertakan header `Content-Disposition` (RFC 5987 UTF-8), `Repr-Digest` (RFC 9530), dan `Cache-Control: no-store`.

### Aktivitas (Audit Log)
- Pencatatan otomatis `upload`, `download`, `share_image` — hanya dicatat saat operasi **berhasil**.
- Filter berdasarkan aksi, rentang tanggal, serta paginasi.
- Log **tanpa data pasien**: hanya aksi, waktu, dan `file_id`.

### Benchmark Kriptografi
- `POST /benchmark/run` mengukur **AES-GCM, DES-CBC, dan RC4** melalui jalur kripto produksi yang sama dengan unggahan.
- Metrik: latensi enkripsi/dekripsi, throughput (MB/s), *overhead* ukuran, verifikasi round-trip, dan **deteksi manipulasi** (*tamper detection*).
- Frontend menampilkan visualisasi perbandingan via Recharts.

### Stenganografi & Reveal Identitas
- Citra klinis yang dibagikan (`share-image`) menyisipkan identitas pasien (nama, MRN, tanggal lahir, diagnosis) **terenkripsi AES-256-CBC** ke dalam piksel gambar menggunakan **LSB steganography**.
- Kunci diturunkan dari *user id* pengunggah menggunakan **scrypt** (N=2¹⁵, r=8, p=1).
- `POST /stego/reveal` mengekstrak dan mendekripsi identitas dari PNG/JPEG yang dibagikan.

---

## Arsitektur Sistem

```text
┌───────────────────────────┐        HTTP / JSON + multipart
│        Next.js 16         │  ─────────────────────────────────────┐
│  React 19 · TanStack      │                                       │
│  Query · Tailwind 4       │  Bearer JWT (sessionStorage)          │
└───────────────────────────┘                                       ▼
                                              ┌──────────────────────────────────┐
                                              │            FastAPI               │
                                              │  router → service → repository   │
                                              │  (validasi, kripto, otorisasi)   │
                                              └───────┬───────────────┬──────────┘
                                                      │               │
                                    SQLAlchemy / psycopg3      MinIO SDK (S3 API)
                                                      │               │
                                              ┌───────▼──────┐  ┌─────▼───────────┐
                                              │  PostgreSQL  │  │ Object Storage  │
                                              │ metadata +   │  │ archives/       │
                                              │ ciphertext   │  │ <file_id>.bin   │
                                              └──────────────┘  └─────────────────┘
```

### Lapisan Backend

| Lapisan | Direktori | Tanggung jawab |
| :--- | :--- | :--- |
| **Router** | `app/routers/` | Endpoint HTTP, dependency injection, pembentukan respons envelope |
| **Schema** | `app/schemas/` | Kontrak request/response Pydantic, hierarki error (`AppError`) |
| **Service** | `app/services/` | Logika bisnis: kripto berkas/pasien, validasi media, stego, benchmark |
| **Repository** | `app/repositories/` | Query SQL ter-*scope* oleh pemilik (`WHERE owner_id = :me`) |
| **Model** | `app/models/` | ORM SQLAlchemy + constraint tingkat database |
| **Core** | `app/core/` | Config env, JWT & hashing, middleware logging, exception handlers |

### Lapisan Frontend

```text
src/
├── app/
│   ├── (auth)/login, (auth)/register   # Rute publik
│   ├── (app)/patients/[id]             # Daftar & detail pasien + berkas
│   ├── (app)/logs                      # Audit log pengguna
│   ├── (app)/benchmark                 # Perbandingan cipher
│   └── (app)/reveal                    # Unggah citra untuk membuka identitas
├── components/                         # UI shadcn/base-ui, per domain
└── lib/
    ├── api/      # Klien fetch, tipe, penanganan error
    ├── auth/     # Penyimpanan token, hook sesi
    ├── files/    # Aturan kategori, pengunduhan
    └── stego/    # Alur reveal
```

---

## Model Keamanan

### 1. Format Kontainer `SIA1`

Setiap objek terenkripsi diserialisasi ke format biner terpadu:

```text
┌──────────┬───────────┬──────────────┬───────────────┬─────────────────┐
│  "SIA1"  │ cipher_id │  IV / nonce  │  ciphertext   │  tag / HMAC     │
│  4 byte  │  1 byte   │ 0/8/12 byte  │   variabel    │ 16 atau 32 byte │
└──────────┴───────────┴──────────────┴───────────────┴─────────────────┘
```

| `cipher_id` | Algoritma | Panjang kunci | IV | Autentikasi |
| :---: | :--- | :---: | :---: | :--- |
| `1` | **AES-256-GCM** | 32 B | 12 B nonce | GCM tag 16 B (AEAD) |
| `2` | **DES-CBC + PKCS#7** | 8 B | 8 B | HMAC-SHA256 32 B (encrypt-then-MAC) |
| `3` | **RC4-drop3072** | 16 B | — | HMAC-SHA256 32 B (encrypt-then-MAC) |

> AES-GCM adalah default dan satu-satunya algoritma yang direkomendasikan untuk produksi. DES dan RC4 disediakan **untuk keperluan akademik/perbandingan**; frontend secara eksplisit menandai keduanya sebagai "hanya untuk perbandingan".

### 2. Envelope Encryption (DEK + Master Key)

```text
Master Key (MASTER_KEY, 32 byte base64) ──AES-256-GCM──► wrapped DEK
                                                             │
plaintext ──AES-256-GCM(DEK, AAD)──► SIA1 blob ──────────────┘ (DEK hanya hidup saat request)
```

- Setiap berkas memiliki **DEK acak** (dan **MAC key** terpisah untuk DES/RC4) yang dibungkus dengan master key.
- Master key **tidak pernah** masuk ke database; hanya tersedia di environment variable.
- Mendukung **key rotation** melalui `rewrap_value()` (diuji di `tests/test_rotation.py`).

### 3. Ikatan AAD (Anti Replay / Anti Swap)

AAD = `owner_id.bytes || file_id.bytes` (atau `owner_id || patient_id` untuk rekaman pasien).

Konsekuensi: menyalin ciphertext ke baris lain atau akun lain akan **gagal verifikasi** (422) alih-alih terdekripsi — terjaga meski penyerang memiliki akses tulis ke database.

### 4. Verifikasi Berlapis pada Unduh

1. Fetch objek dari storage (`404` bila hilang).
2. Verifikasi tag AEAD/HMAC → jika gagal dan tag objek **berbeda** dari `files.auth_tag` ⇒ `409` (objek tertukar); jika sama ⇒ `422` (byte dimanipulasi).
3. Bandingkan **SHA-256 plaintext** dengan digest yang disimpan ⇒ `422` bila tidak cocok.

Semua verifikasi selesai **sebelum** satu byte pun dikirim ke klien.

### 5. Privasi Rekaman Pasien

- Satu blob AES-256-GCM per pasien (`AAD = owner_id || patient_id`).
- **Nonce baru** pada setiap pembaruan (mencegah *nonce reuse* yang fatal untuk GCM).
- Daftar pasien tidak mengirim diagnosis dan mem-mask NIK.

### 6. Anti-IDOR

Seluruh query repository mencakup `owner_id` pada klausa `WHERE`. Pasien/berkas milik akun lain menghasilkan **404 yang identik** dengan yang tidak ada — tidak membocorkan keberadaan ID.

### 7. Matriks Kode Error

| HTTP | Kode | Makna |
| :---: | :--- | :--- |
| 400 | `email_already_registered`, `username_already_taken`, `not_shareable` | Konflik input / berkas tidak dapat dibagikan |
| 401 | `unauthorized`, `invalid_credentials` | Token hilang/kedaluwarsa/rusak, kredensial salah |
| 404 | `not_found` | Sumber daya tidak ada **atau** bukan milik pengguna |
| 409 | `conflict` | Objek valid namun bukan milik baris tersebut |
| 413 | `file_too_large` | Melebihi 100 MiB |
| 415 | `unsupported_file_type`, `unsupported_image_type` | MIME tidak sesuai kategori |
| 422 | `validation_error`, `integrity_failed`, `reveal_failed` | Validasi input / integritas gagal |
| 503 | `storage_unavailable` | Object storage tidak dapat dijangkau |

Format respons seragam:

```json
{
  "success": false,
  "error": { "code": "integrity_failed", "message": "File integrity check failed", "details": {} }
}
```

---

## Referensi API

Semua endpoint (kecuali `health`, `auth`, dan `benchmark`) memerlukan header `Authorization: Bearer <jwt>`.

### Autentikasi

| Metode | Path | Deskripsi |
| :--- | :--- | :--- |
| `POST` | `/auth/register` | Buat akun baru (`name`, `email`, `password`) → 201 |
| `POST` | `/auth/login` | Verifikasi kredensial → `{ ..., jwt_token }` |

### Pasien

| Metode | Path | Deskripsi |
| :--- | :--- | :--- |
| `GET` | `/patients?page&size` | Daftar pasien (NIK ter-mask, tanpa diagnosis) |
| `POST` | `/patients` | Buat rekaman pasien (terenkripsi) |
| `GET` | `/patients/{patient_id}` | Detail lengkap pasien |
| `PUT` | `/patients/{patient_id}` | Penggantian penuh rekaman (nonce baru) |
| `DELETE` | `/patients/{patient_id}` | Hapus pasien + seluruh berkas & objek |

### Berkas

| Metode | Path | Deskripsi |
| :--- | :--- | :--- |
| `POST` | `/patients/{patient_id}/files` | Multipart: `file`, `category`, `cipher` (`aes`\|`des`\|`rc4`) |
| `GET` | `/patients/{patient_id}/files?page&size&category` | Daftar berkas pasien |
| `GET` | `/files/{file_id}` | Metadata berkas (tanpa akses storage) |
| `GET` | `/files/{file_id}/download` | Unduh berkas asli (verifikasi + header keamanan) |
| `POST` | `/files/{file_id}/share-image` | Citra klinis dengan identitas tersisip (stego) |

### Aktivitas, Stego & Benchmark

| Metode | Path | Deskripsi |
| :--- | :--- | :--- |
| `GET` | `/logs?page&size&action&date_from&date_to` | Audit log milik pengguna |
| `POST` | `/stego/reveal` | Multipart `file` PNG/JPEG → identitas pasien |
| `POST` | `/benchmark/run` | Body opsional `size_bytes` (1 KiB–10 MiB), `iterations` (1–10) |
| `GET` | `/health` | Health check |

**Contoh — unduh berkas:**

```bash
curl -s -OJ -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/files/<file_id>/download"
```

**Contoh — benchmark:**

```bash
curl -s -X POST http://localhost:8000/benchmark/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"size_bytes": 1048576, "iterations": 5}'
```

> Dokumentasi interaktif lengkap tersedia di **`/docs`** (Swagger UI) dan **`/redoc`** saat server berjalan.

---

## Teknologi

| Kategori | Backend (`apps/api`) | Frontend (`apps/web`) |
| :--- | :--- | :--- |
| Runtime / Framework | Python ≥ 3.11, **FastAPI**, Uvicorn / Granian | Node.js 20+, **Next.js 16** (App Router), React 19 |
| Database | PostgreSQL, **SQLAlchemy 2**, Alembic | — |
| Storage | **MinIO** (S3-compatible) | — |
| Kriptografi | `cryptography`, `pycryptodome`, **pyjwt**, `pwdlib`/Argon2 | — |
| Steganografi | `Pillow`, `numpy`, `jpeglib` | — |
| Data & Form | Pydantic v2, `pydantic-settings` | TanStack Query, react-hook-form, Zod |
| UI & Styling | — | Tailwind CSS 4, shadcn/base-ui, lucide-react, Recharts, sonner |
| Kualitas | pytest, pytest-cov, ruff | ESLint, TypeScript (`strict`), Vitest |

---

## Struktur Repositori

```text
SiArsip/
├── apps/
│   ├── api/                     # Backend FastAPI
│   │   ├── app/
│   │   │   ├── core/            # config, security (JWT/hash), deps, handlers, middleware
│   │   │   ├── db/              # engine & session, Base
│   │   │   ├── models/          # User, Patients, Files, ActivityLogs, enums
│   │   │   ├── repositories/    # Query owner-scoped
│   │   │   ├── routers/         # auth, patients, files, logs, stego, benchmark, health
│   │   │   ├── schemas/         # Request/response + errors/
│   │   │   └── services/
│   │   │       ├── crypto/      # Container SIA1, AES, DES, RC4, registry, envelope
│   │   │       ├── file_crypto.py / patient_crypto.py
│   │   │       ├── file_service.py / patient_service.py
│   │   │       ├── storage.py   # Abstraksi MinIO
│   │   │       ├── stego.py / stego_service.py
│   │   │       └── benchmark_service.py
│   │   ├── alembic/versions/    # Riwayat migrasi database
│   │   ├── scripts/dev_schema.py
│   │   ├── tests/               # Suite pytest (berbasis PostgreSQL)
│   │   ├── main.py              # Entry point ASGI
│   │   └── pyproject.toml
│   └── web/                     # Frontend Next.js
│       ├── src/app/             # Rute App Router
│       ├── src/components/      # UI per domain
│       ├── src/lib/             # Klien API, auth, aturan berkas, stego
│       └── package.json
├── bench/                       # (disediakan) skrip benchmark & load testing
├── docs/
│   ├── crypto-format.md         # Spesifikasi kontainer SIA1
│   ├── api-requests-from-frontend.md
│   └── wireframes.md
├── .github/                     # Workflow CI/CD, CODEOWNERS, template PR
└── .env.example
```

---

## Memulai (Quick Start)

### Prasyarat

- **Python ≥ 3.11** (CI menggunakan 3.12)
- **Node.js ≥ 20** dan npm
- **PostgreSQL 16** (lokal atau container)
- **MinIO** atau layanan S3-compatible
- Opsional: [`uv`](https://docs.astral.sh/uv/) sebagai pengelola paket Python

### 1. Klon & konfigurasi environment

```bash
git clone <repository-url>
cd SiArsip
cp .env.example .env
cp apps/web/.env.example apps/web/.env.local
```

Hasilkan master key 32 byte yang aman:

```bash
python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
```

### 2. Jalankan dependensi (Docker)

```bash
# PostgreSQL
docker run -d --name siarsip-db \
  -e POSTGRES_USER=siarsip -e POSTGRES_PASSWORD=siarsip -e POSTGRES_DB=siarsip \
  -p 5432:5432 postgres:16

# MinIO
docker run -d --name siarsip-minio \
  -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin \
  -p 9000:9000 -p 9001:9001 minio/minio server /data --console-address ":9001"
```

### 3. Siapkan backend

```bash
cd apps/api

# Menggunakan uv (disarankan)
uv sync

# atau pip
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-cov

# Terapkan skema database
alembic upgrade head

# Jalankan server pengembangan
uvicorn main:app --reload --port 8000
# atau: granian --interface asgi main:app --reload
```

API tersedia di `http://localhost:8000` — cek `GET /health`, lalu buka `http://localhost:8000/docs`.

### 4. Siapkan frontend

```bash
cd apps/web
npm ci
npm run dev
```

Aplikasi web tersedia di `http://localhost:3000` (root otomatis mengarah ke `/patients`).

---

## Konfigurasi Environment

Letakkan file `.env` di **root repositori** (dibaca backend melalui `python-dotenv`).

| Variabel | Wajib | Deskripsi |
| :--- | :---: | :--- |
| `DATABASE_URL` | ✅ | Contoh: `postgresql+psycopg://user:pass@localhost:5432/siarsip` |
| `SECRET_KEY` | ✅ | Kunci penandatanganan JWT; gunakan string acak panjang |
| `ALGORITHM` | — | Algoritma JWT (default `HS256`) |
| `MASTER_KEY` | ✅ | **Base64 dari tepat 32 byte**; membungkus semua DEK |
| `AWS_ENDPOINT_URL_S3` | ✅ | Contoh: `http://localhost:9000` |
| `AWS_ACCESS_KEY_ID` | ✅ | Kredensial MinIO/S3 |
| `AWS_SECRET_ACCESS_KEY` | ✅ | Kredensial MinIO/S3 |
| `AWS_REGION_NAME` | — | Region S3 (opsional untuk MinIO) |
| `BUCKET_NAME` | — | Default `siarsip`; bisa diturunkan dari path endpoint |

Frontend (`apps/web/.env.local`):

| Variabel | Deskripsi |
| :--- | :--- |
| `NEXT_PUBLIC_API_URL` | Base URL backend tanpa slash di akhir (default `http://localhost:8000`) |

> **NOTE:** `MASTER_KEY` harus tepat 32 byte setelah decode base64. Kehilangan master key berarti seluruh DEK—dan karenanya seluruh data—tidak dapat dipulihkan. Jangan pernah melakukan commit pada file `.env`.

---

## Database & Migrasi

Skema dikelola sepenuhnya dengan **Alembic**. Riwayat revisi (urut):

1. `a1d68b0121d6` — initial migration (basis kosong)
2. `c814d01543ea` — create the database scheme
3. `100471ae24fd` — create the database scheme
4. `dd1a2b3c4d5e` — align schema with ER diagram
5. `7e9a62f539df` — fix some of the database scheme
6. `c4eaf83543f1` — enforce file integrity & cascade delete
7. `f73a32efb9e9` — add `name` on users
8. `82ef1308e7df` — add name to users
9. `dde2914f108d` — add `share_image` activity action
10. `e5f6a7b8c9d0` — add `share_image` to activity action (idempoten)

```bash
cd apps/api

alembic upgrade head                  # Terapkan semua migrasi
alembic revision --autogenerate -m "deskripsi"   # Buat revisi baru
alembic downgrade -1                  # Kembali satu langkah
```

**Isolasi skema pengujian** — `scripts/dev_schema.py` membuat skema PostgreSQL sementara agar tes tidak menyentuh data pengembangan:

```bash
uv run --env-file ../../.env python scripts/dev_schema.py up    # buat + migrasi
uv run --env-file ../../.env python scripts/dev_schema.py test  # jalankan tes skema
uv run --env-file ../../.env python scripts/dev_schema.py drop  # hapus skema
```

### Model Data

```text
users ──1:N──< patients ──1:N──< files
  │                                  │
  └──────────1:N──< activity_logs >──┘   (file_id opsional; user_id opsional)
```

- **users**: `id (uuid)`, `name` (unik), `email` (unik), `password_hash`, `stego_key_wrapped`, `created_at`
- **patients**: `data_encrypted`, `data_nonce` (12 B, CHECK), `dek_wrapped`, timestamps
- **files**: metadata + kolom kripto (`algorithm`, `iv`, `auth_tag`, `dek_wrapped`, `mac_key_wrapped`, `sha256_plain`, `storage_key` unik) dengan CHECK constraint konsistensi algoritma↔IV↔MAC key
- **activity_logs**: `bigint` PK, `action` (enum), `user_id`/`file_id` nullable, `created_at` timestamptz

---

## Pengujian

### Backend (pytest)

Tes backend membutuhkan **PostgreSQL yang dapat dijangkau** (fixture akan `skip` bila tidak tersedia). Semua operasi berjalan dalam transaksi yang selalu di-`rollback`, sehingga database tidak tercemar.

```bash
cd apps/api

export TEST_DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/siarsip_test"
export MASTER_KEY="$(python -c 'import base64,os;print(base64.b64encode(os.urandom(32)).decode())')"
export SECRET_KEY="dev-secret"

pytest -v                      # Seluruh suite
pytest --cov=app --cov-report=term-missing   # Dengan coverage
ruff check .                   # Lint
```

Cakupan tes (± 144 kasus) mencakup:

| Modul | Fokus |
| :--- | :--- |
| `test_auth.py` | Registrasi, duplikasi, validasi, login, validitas JWT |
| `test_patients.py` | Round-trip, nonce unik, masking NIK, isolasi antar-pengguna, manipulasi ciphertext |
| `test_files.py` | Round-trip per cipher, penyamaran MIME, batas ukuran, IDOR, `409/422` integritas, penanganan activity log |
| `test_crypto.py` / `test_envelope.py` | AEAD/HMAC, AAD salah, magic invalid, wrap/unwrap DEK |
| `test_integrity.py` | SHA-256 round-trip pada 5 ukuran (1 KB–50 MB), bit-flip di setiap bagian kontainer |
| `test_rotation.py` | Rotasi master key (*rewrap*) end-to-end |
| `test_stego.py` | Embed/extract LSB pada PNG & JPEG, kata sandi salah, kapasitas |
| `test_benchmark.py` | Autentikasi, default, validasi parameter, tiga algoritma |
| `test_db_schema.py` | Snapshot katalog: tabel, kolom, FK, CHECK constraint |
| `test_logs.py` | Filtering, paginasi, scope kepemilikan |

### Frontend (Vitest + lint + typecheck)

```bash
cd apps/web
npm test          # Vitest (ciphers, format, client, errors, rules, save, stego, logs)
npm run lint      # ESLint (Next.js core-web-vitals + TypeScript)
npm run typecheck # next typegen && tsc --noEmit
npm run build     # Production build check
```

---

## CI/CD & Deployment

Dua workflow GitHub Actions, dipicu oleh PR maupun push ke `main`:

**`ci-cd.yml` — Backend**

1. Menjalankan service **PostgreSQL 16**.
2. Instal dependensi → `alembic upgrade head` → `pytest tests/ -v`.
3. **Deploy** ke Vercel (hanya push ke `main`, memakai `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`).

**`frontend.yml` — Frontend** (hanya jika `apps/web/**` berubah)

1. `npm ci` → `npm run lint` → `npm run typecheck` → `npm test` → `npm run build`.
2. **Deploy** ke Vercel (`VERCEL_WEB_PROJECT_ID`).

CORS backend secara eksplisit mengizinkan origin `https://siarsip-fe.vercel.app`.

---

## Konvensi Tim

### 1. Branch

```text
feature/SIA-<nomor_tiket>-<deskripsi_singkat>
```

Contoh: `feature/SIA-11-initial-monorepo-setup`

### 2. Commit Message

```text
SIA-<nomor_tiket>: <pesan deskripsi>
```

Contoh: `SIA-11: siapkan struktur folder monorepo dan README`

### 3. Pull Request & Review

- Branch `main` **terproteksi**.
- Semua perubahan wajib melalui **Pull Request** dengan minimal **1 approval**.
- Template PR memuat *Definition of Done*: linting bersih, format commit benar, reviewer disetujui, tanpa secret tersimpan.

### 4. Code Owners

| Path | Owner |
| :--- | :--- |
| `apps/api/` | @Ryu2804, @AneKazek |
| `apps/web/` | @masterzaff |
| `bench/` | @HeptaZ |
| `docs/` | @Ryu2804 |

### 5. Gaya Kode

- **Python**: Ruff (`line-length = 100`, target `py311`, aturan `E,F,I,B,UP`).
- **TypeScript**: ESLint + `strict` mode; komponen server/client dipisah eksplisit.

---

## Dokumentasi Lanjutan

| Dokumen | Isi |
| :--- | :--- |
| [`docs/crypto-format.md`](docs/crypto-format.md) | Spesifikasi biner kontainer `SIA1` dan penurunan AAD |
| [`docs/api-requests-from-frontend.md`](docs/api-requests-from-frontend.md) | Status kebutuhan endpoint dari tim frontend |
| [`docs/wireframes.md`](docs/wireframes.md) | Rancangan antarmuka |
| `apps/api/app/services/crypto/` | Docstring implementasi per cipher |
| `/docs` (runtime) | OpenAPI / Swagger interaktif |

---

## Error Map

| Gejala | Penyebab umum | Solusi |
| :--- | :--- | :--- |
| `RuntimeError: MASTER_KEY ... 32 byte` | Base64 tidak valid / panjang salah | Regenerasi dengan perintah pada [Quick Start](#1-klon--konfigurasi-environment) |
| `503 storage_unavailable` | MinIO tidak berjalan / kredensial salah | Cek container MinIO & variabel `AWS_*`; bucket dibuat otomatis |
| Tes di-*skip* (`database is unreachable`) | `DATABASE_URL`/`TEST_DATABASE_URL` kosong | Set variabel dan pastikan PostgreSQL aktif |
| `422 integrity_failed` saat unduh | Objek dimanipulasi / master key berubah | Jika master key diganti, lakukan *rewrap* seluruh DEK |
| `409 conflict` pada unduh | Objek tertukar antar baris | Periksa integritas storage; AAD menggagalkan swap |
| CORS error di browser | Origin frontend tidak diizinkan | Sesuaikan daftar `allow_origins` di `apps/api/main.py` |
| Unggahan ditolak `415` | Magic bytes ≠ kategori / berkas executable | Gunakan berkas media valid sesuai [tabel kategori](#manajemen-berkas-medis) |

---


## Lisensi

Proyek ini dikembangkan untuk keperluan akademik (mata kuliah **Keamanan Informasi**) tanpa adanya plagiarisme dari pihak manapun

<div align="center">
<sub>Benedictus Ryu Gunawan - Muhammad Irzam Hafis Fabiansyah - Jonathan Joyo Wibowo - Muhammad Dzaky Haidar</sub>
</div>
