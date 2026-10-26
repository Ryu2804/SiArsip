# Wireframe frontend SiArsip (MVP)

Wireframe low-fi untuk SIA-18. Fokus pada isi, urutan, dan status tiap layar; bukan tampilan akhir.
Semua teks antarmuka berbahasa Indonesia. Tidak ada data pasien nyata, semua contoh fiktif.

## Prinsip yang berlaku di semua layar

- Rute memakai UUID (`/patients/<uuid>`), tidak pernah nama atau No. RM.
- Nama atau No. RM pasien tidak dimasukkan ke judul tab (`<title>`) maupun URL.
- Setiap layar punya tiga status selain konten normal: **memuat**, **kosong**, **galat**.
- Aksi merusak (hapus) selalu meminta konfirmasi di dalam halaman.
- Status keamanan cipher tampil sebagai **teks**, tidak hanya warna.
- Dapat dipakai di tablet (perawat di bangsal): target sentuh minimal 44 px, tabel bisa digulir ke samping.

## Kerangka halaman (setelah masuk)

```
+--------------------------------------------------------------+
| SiArsip   Pasien | Ungkap identitas | Benchmark | Log   [Nama]  [Keluar] |
+--------------------------------------------------------------+
|                                                              |
|   (isi halaman)                                              |
|                                                              |
+--------------------------------------------------------------+
```

---

## 1. Masuk / Daftar

Rute `/login`, `/register`. API: `POST /auth/login`, `POST /auth/register`.

```
          SiArsip
  Arsip digital terenkripsi untuk dokumentasi pasien
 +----------------------------------------+
 | Masuk                                  |
 |                                        |
 | Email                                  |
 | [______________________________]       |
 | Kata sandi                             |
 | [______________________________]       |
 |                                        |
 | [            Masuk              ]      |
 |                                        |
 | Belum punya akun? Daftar               |
 +----------------------------------------+
```

- Galat per kolom di bawah kolom; galat umum (kredensial salah) di kotak di atas formulir.
- Tombol berubah menjadi "Memproses…" dan nonaktif saat dikirim.
- `/register` menambah kolom **Nama** di atas Email.

## 2. Daftar pasien

Rute `/patients`. API: `GET /patients`.

```
 Pasien                                    [ + Tambah pasien ]
 [ Cari nama atau No. RM ____________ ]

 +----------+--------------+----------------+-------------+
 | No. RM   | Nama         | NIK            | Tgl. lahir  |
 +----------+--------------+----------------+-------------+
 | RM-0001  | (nama)       | 3201********01 | 12 Mei 1980 |  >
 | RM-0002  | (nama)       | -              | -           |  >
 +----------+--------------+----------------+-------------+
```

- Pencarian di sisi klien berdasarkan nama atau No. RM.
- NIK selalu tampil tersamar (`nik_masked` dari API).
- Klik baris membuka detail pasien.
- Kosong: "Belum ada pasien. Tambahkan pasien pertama." + tombol tambah.
- "Tambah pasien" membuka formulir (modal): No. RM*, Nama*, NIK (16 digit), Tanggal lahir, Diagnosis.

## 3. Detail pasien + daftar file

Rute `/patients/[id]`. API: `GET /patients/{id}`, `PUT`, `DELETE`; daftar file dan unduh dari `/files/...`.

```
 < Pasien
 +------------------------------------------------------------+
 | (Nama pasien)                       [ Ubah ]  [ Hapus ]    |
 | No. RM RM-0001   NIK 3201************01   Lahir 12 Mei 1980|
 | Diagnosis: ...                                             |
 +------------------------------------------------------------+

 File                                         [ + Unggah file ]
 +--------------+-----------+--------+---------+-----------+--------+
 | Nama file    | Kategori  | Ukuran | Cipher  | Diunggah  | Aksi   |
 +--------------+-----------+--------+---------+-----------+--------+
 | rontgen.png  | Citra     | 2,1 MB | [AES-GCM]| 26 Okt   | Lihat  |
 |              | klinis    |        |         |           | Unduh  |
 |              |           |        |         |           | Unduh untuk konsultasi |
 | ktp.jpg      | Scan      | 0,4 MB | [DES-CBC]| 26 Okt   | Lihat  |
 |              | identitas |        |         |           | Unduh  |
 +--------------+-----------+--------+---------+-----------+--------+
```

- "Hapus" membuka konfirmasi di dalam halaman yang menyebut jumlah file yang ikut terhapus.
- "Unduh untuk konsultasi" hanya muncul pada kategori **Citra klinis** (`shareable`).
- "Lihat" membuka pratinjau (modal) untuk gambar, PDF, dan video.
- Galat integritas (409): pesan jelas "Integritas file gagal diverifikasi", bukan galat generik.
- Kosong: "Belum ada file untuk pasien ini."

## 4. Unggah file

Dialog dari halaman detail pasien. API: `POST /patients/{id}/files` (multipart: `file`, `category`, `cipher`).

```
 +--------------------------------------------------+
 | Unggah file                                  [x] |
 |                                                  |
 |  +--------------------------------------------+  |
 |  |   Tarik file ke sini, atau pilih file      |  |
 |  |   Maks. 100 MB                             |  |
 |  +--------------------------------------------+  |
 |  rontgen.png  (2,1 MB)                  [ Hapus ]|
 |                                                  |
 |  Kategori   [ Citra klinis              v ]      |
 |  Cipher     [ AES-GCM - Direkomendasikan v ]     |
 |             Standar modern dengan autentikasi... |
 |                                                  |
 |  [==========----------]  54%                     |
 |                                                  |
 |                          [ Batal ] [ Unggah ]    |
 +--------------------------------------------------+
```

- Opsi cipher: **AES-GCM** (bawaan, "Direkomendasikan"), **DES-CBC** dan **RC4** (lencana "Tidak disarankan" + catatan satu baris).
- File > 100 MB ditolak di klien sebelum dikirim.
- Galat 413 "Ukuran file melebihi batas", 415 "Jenis file tidak didukung".
- Sukses: dialog menutup, toast "File berhasil diunggah", daftar file diperbarui.

## 5. Ungkap identitas

Rute `/reveal`. API: `POST /stego/reveal` (SIA-122, sudah ada di backend).

```
 Ungkap identitas
 Unggah gambar konsultasi (PNG) untuk melihat identitas yang tersemat.

 +--------------------------------------------+
 |   Tarik gambar PNG ke sini, atau pilih     |
 +--------------------------------------------+
 [ Ungkap identitas ]

 (hasil)
 +--------------------------------------------+
 | Identitas ditemukan                        |
 | No. RM   RM-0001                           |
 | Nama     (nama pasien)                     |
 +--------------------------------------------+
   atau
 +--------------------------------------------+
 | Tidak ada identitas pada gambar ini.       |
 +--------------------------------------------+

 ! Identitas hilang jika gambar dikirim ulang sebagai JPEG
   (misalnya lewat WhatsApp). Kirim sebagai berkas PNG.
```

- Peringatan JPEG selalu terlihat sebelum dan sesudah hasil, tidak disembunyikan.
- Hasil identitas tidak pernah masuk judul tab atau URL.

## 6. Benchmark

Rute `/benchmark`. API: `POST /benchmark/run` (SIA-131, sudah ada di backend).

```
 Benchmark cipher                              [ Jalankan ]
 (memuat…) saat berjalan; tombol nonaktif

 Throughput (MB/s)                 Overhead ukuran (%)
 AES  |############ enkripsi        AES  |##
      |###########  dekripsi       DES  |####
 DES  |####                        RC4  |#
 RC4  |######

 +--------+-------+--------+----------+----------+------------+
 | Cipher | Enk.  | Dek.   | Overhead | Keutuhan | Deteksi    |
 |        | MB/s  | MB/s   | (%)      |          | manipulasi |
 +--------+-------+--------+----------+----------+------------+
 | AES    | ...   | ...    | ...      | Ya       | 100%       |
 | DES    | ...   | ...    | ...      | Ya       | 100%       |
 | RC4    | ...   | ...    | ...      | Ya       | ...%       |
 +--------+-------+--------+----------+----------+------------+

 Catatan keamanan
 - AES-GCM: direkomendasikan.
 - DES-CBC: usang (kunci 56-bit).
 - RC4: usang (bias keystream).
```

- Grafik batang disertai tabel angka, sehingga informasi tidak bergantung pada warna.
- Belum pernah dijalankan: "Belum ada hasil. Tekan Jalankan."

---

## Pertanyaan terbuka untuk PM

1. Nama pengguna harus unik di backend (`username_already_taken`). Apakah itu memang diinginkan, atau cukup email yang unik?
2. Layar log aktivitas (SIA-134) tidak termasuk 6 layar di tiket ini. Apakah cukup tabel sederhana dengan filter jenis aksi?
3. Tidak ada endpoint logout; tombol "Keluar" hanya menghapus sesi di browser. Apakah aksi logout perlu tercatat di log?
