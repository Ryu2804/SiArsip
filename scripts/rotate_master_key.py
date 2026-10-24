import argparse
import base64
import sys
from sqlalchemy import text
from app.db.database import SessionLocal
from app.services.crypto.envelope import wrap_key, unwrap_key
from app.services.crypto.exceptions import IntegrityError

def rewrap_value(wrapped: bytes | None, old_key: bytes, new_key: bytes) -> bytes | None:
    if not wrapped:
        return None
    raw_secret = unwrap_key(wrapped, master_key=old_key)
    return wrap_key(raw_secret, master_key=new_key)

def rotate_database_keys(old_master_key: bytes, new_master_key: bytes) -> tuple[int, int]:
    db = SessionLocal()
    files_updated = 0
    users_updated = 0

    try:
        # 1. Rotasi tabel users (stego_key_wrapped)
        users = db.execute(text("SELECT id, stego_key_wrapped FROM users WHERE stego_key_wrapped IS NOT NULL")).fetchall()
        for user in users:
            new_stego_wrapped = rewrap_value(user.stego_key_wrapped, old_master_key, new_master_key)
            db.execute(
                text("UPDATE users SET stego_key_wrapped = :val WHERE id = :id"),
                {"val": new_stego_wrapped, "id": user.id}
            )
            users_updated += 1

        # 2. Rotasi tabel files (dek_wrapped & mac_key_wrapped)
        # Gunakan raw SQL agar aman jika model ORM file belum selesai dibuat rekan tim
        try:
            files = db.execute(text("SELECT id, dek_wrapped, mac_key_wrapped FROM files")).fetchall()
            for file_row in files:
                new_dek = rewrap_value(file_row.dek_wrapped, old_master_key, new_master_key)
                new_mac = rewrap_value(file_row.mac_key_wrapped, old_master_key, new_master_key)
                db.execute(
                    text("UPDATE files SET dek_wrapped = :dek, mac_key_wrapped = :mac WHERE id = :id"),
                    {"dek": new_dek, "mac": new_mac, "id": file_row.id}
                )
                files_updated += 1
        except Exception as e:
            # Lewati tabel files hanya jika tabelnya memang belum di-migrate di database lokal
            if "no such table: files" not in str(e).lower():
                raise e

        # Simpan perubahan dalam 1 transaksi atomik
        db.commit()
        return users_updated, files_updated
    except IntegrityError:
        db.rollback()
        raise RuntimeError("Rotasi dibatalkan: OLD_MASTER_KEY salah atau ada data kunci yang rusak!")
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Rotasi gagal karena kesalahan sistem: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rotasi master key pada database SiArsip")
    parser.add_argument("--old-key", required=True, help="Master key lama (base64)")
    parser.add_argument("--new-key", required=True, help="Master key baru (base64)")
    args = parser.parse_args()

    try:
        old_k = base64.b64decode(args.old_key)
        new_k = base64.b64decode(args.new_key)
        if len(old_k) != 32 or len(new_k) != 32:
            raise ValueError("Kunci harus tepat 32 byte.")
    except Exception as err:
        print(f"Error parsing kunci: {err}", file=sys.stderr)
        sys.exit(1)

    print("Memulai rotasi kunci...")
    u_count, f_count = rotate_database_keys(old_k, new_k)
    print(f"Rotasi selesai: {u_count} user dan {f_count} file berhasil di-update.")