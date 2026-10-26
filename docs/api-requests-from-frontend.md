# Status endpoint untuk frontend

Daftar kebutuhan endpoint dari sisi frontend. Bagian yang berstatus "USULAN" adalah
saran dari frontend, bukan spesifikasi yang sudah disepakati.

## Sudah ada dan dipakai frontend

- `GET /patients/{patient_id}/files?page&size&category`: daftar file pasien (SIA-111).
- `GET /logs?page&size&action&date_from&date_to`: log aktivitas milik pengguna (SIA-134).
- `GET /files/{id}/download` dan `POST /files/{id}/share-image`: unduh dan unduh untuk konsultasi.

## Belum ada

| Isu | Kebutuhan | Status |
| --- | --- | --- |
| SIA-122 / #43 | `POST /stego/reveal` (menerima PNG, mengembalikan identitas bila milik pengguna) | Disebut di issue #43; bentuk respons belum ada. |
| SIA-131 / #46 | Hasil benchmark cipher | USULAN: per cipher `algorithm`, `size_bytes`, `encrypt_ms`, `decrypt_ms` agar bisa digrafikkan. |

## Catatan kecil

- Error pasien memakai `error_code`, error lain memakai `code`. Frontend mengerti keduanya
  untuk saat ini, tetapi seragam lebih baik.
