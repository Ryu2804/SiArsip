# Format Kontainer SIA1

Semua data terenkripsi disimpan dalam format kontainer biner terpadu `SIA1`.

## Struktur Biner

| Komponen | Ukuran | Deskripsi |
|---|---|---|
| Magic Header | 4 byte | Karakter ASCII `SIA1` |
| Cipher ID | 1 byte | Identifier cipher (`1`: AES-GCM, `2`: DES-CBC, `3`: RC4) |
| Nonce / IV | Variabel | `12 byte` untuk AES, `8 byte` untuk DES, `0 byte` untuk RC4 |
| Ciphertext | Variabel | Payload data terenkripsi |
| Tag / HMAC | Variabel | `16 byte` (GCM Tag) atau `32 byte` (HMAC-SHA256) |

## Associated Authenticated Data (AAD)
Untuk mencegah penukaran file antar akun atau rekaman, AAD dirangkai dengan format:
`AAD = f"{user_id}:{file_id}".encode("utf-8")`