# Permintaan endpoint dari frontend

Endpoint yang dibutuhkan frontend tetapi belum ada di `apps/api`. Bentuk respons
mengikuti envelope yang sudah dipakai (`{success, message, data, meta}`).

## 1. Daftar file pasien (blocker SIA-111 / #40, juga SIA-125 / #44)

`GET /patients/{patient_id}/files`

- Auth: Bearer token, sama seperti `GET /files/{file_id}`.
- Query: `page` (default 1), `size` (default 20, maks 100), `category` (opsional).
- Urutan: `created_at` menurun.
- `data`: list `FileResponse` (skema yang sama dengan upload / `GET /files/{id}`).
  Field yang dipakai UI: `id`, `original_name`, `category`, `pdp_class`, `mime_type`,
  `size_bytes`, `algorithm`, `shareable`, `created_at`.
- `meta`: `{page, size, total}` seperti `GET /patients`.
- Jangan sertakan konten file atau path penyimpanan.
- Pasien tidak ada: 404 dengan `error.code` yang sama seperti endpoint pasien lain.

## 2. Endpoint lain yang masih ditunggu

Frontend sudah menyiapkan kerangka halamannya; kontrak belum ada.

| Isu | Kebutuhan | Catatan |
| --- | --- | --- |
| SIA-122 / #43 | Ungkap identitas (reveal) | Perlu keputusan: apa yang dikembalikan dan apakah dicatat di log. |
| SIA-107 / #39 | Log aktivitas | Usul: `GET /logs?page&size&action&from&to`, tanpa data identitas pasien di payload. |
| SIA-131 / #46 | Benchmark cipher | Usul: hasil per cipher (`algorithm`, `size_bytes`, `encrypt_ms`, `decrypt_ms`) agar bisa digrafikkan. |

## 3. Catatan kecil

- Error pasien memakai `error_code`, error lain memakai `code`. Frontend mengerti keduanya
  untuk saat ini, tetapi seragam lebih baik.
