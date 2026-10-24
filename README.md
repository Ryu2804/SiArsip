# SiArsip

Sistem Manajemen Arsip Digital Terenkripsi.

## Struktur Repositori

```text
.
├── apps/
│   ├── api/        # Backend service / API
│   └── web/        # Frontend web application
├── bench/          # Benchmark & load testing scripts
└── docs/           # Dokumentasi teknis & arsitektur
```

## Konvensi Tim

### 1. Branch
Penamaan branch wajib mengikuti format:
```
feature/SIA-<nomor_tiket>-<deskripsi_singkat>
```
Contoh: `feature/SIA-11-initial-monorepo-setup`

### 2. Commit Message
Format pesan commit wajib mengikuti:
```
SIA-<nomor_tiket>: <pesan deskripsi>
```
Contoh: `SIA-11: siapkan struktur folder monorepo dan README`

### 3. Pull Request & Review
- Branch `main` terproteksi.
- Setiap perubahan wajib diajukan melalui Pull Request (PR) ke `main` dan mendapat minimal 1 review / approval sebelum merge.

## Cara Menjalankan

### Persiapan Environment
1. Salin file environment:
   ```bash
   cp .env.example .env
   ```
2. Sesuaikan konfigurasi variabel environment di file `.env`.

### Menjalankan Layanan
- **API (`apps/api`)**: Jalankan backend service sesuai runtime yang digunakan.
- **Web (`apps/web`)**: Jalankan antarmuka frontend web.
