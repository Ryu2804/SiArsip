# Status endpoint untuk frontend

Daftar kebutuhan endpoint dari sisi frontend. Bagian yang berstatus "USULAN" adalah
saran dari frontend, bukan spesifikasi yang sudah disepakati.

## Sudah ada dan dipakai frontend

- `GET /patients/{patient_id}/files?page&size&category`: daftar file pasien (SIA-111).
- `GET /logs?page&size&action&date_from&date_to`: log aktivitas milik pengguna (SIA-134).
- `GET /files/{id}/download` dan `POST /files/{id}/share-image`: unduh dan unduh untuk konsultasi.

## Status endpoint tambahan

| Isu | Kebutuhan | Status |
| --- | --- | --- |
| SIA-122 / #43 | `POST /stego/reveal` (menerima PNG/JPEG, mengembalikan identitas bila milik pengguna) | Sudah ada: multipart `file`, membalas `patient_id`, `name`, `mrn`, `birth_date`, `diagnosis`. Galat dekripsi: 422 `reveal_failed`. |
| SIA-131 / #46 | Hasil benchmark cipher | Sudah ada: `POST /benchmark/run` (auth), body opsional `size_bytes` (1 KiB–10 MiB) dan `iterations` (1–10). Per cipher: `algorithm`, `size_bytes`, `iterations`, `encrypt_ms`, `decrypt_ms`, total, throughput, overhead, `verified`, `tamper_detected`. |

## Catatan kecil

- Error pasien memakai `error_code`, error lain memakai `code`. Frontend mengerti keduanya
  untuk saat ini, tetapi seragam lebih baik.
