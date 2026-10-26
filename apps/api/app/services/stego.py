import io
import os
import tempfile

import jpeglib
import numpy as np
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from PIL import Image

# Embedded blob layout (after the 4-byte length header):
#   salt (16) | iv (16) | AES-256-CBC ciphertext (PKCS7 padded)
SALT_LEN = 16
IV_LEN = 16
KEY_LEN = 32  # AES-256
_SCRYPT_N = 2**15  # ~0.1 s and 32 MiB per derivation
_SCRYPT_R = 8
_SCRYPT_P = 1


def detect_image_type(data: bytes) -> str | None:
    """Detect by magic bytes, not by filename or client-supplied content type."""
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    return None


# ---------- AES-CBC with a password ----------
def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = Scrypt(salt=salt, length=KEY_LEN, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return kdf.derive(password.encode("utf-8"))


def _encrypt(message: bytes, password: str) -> bytes:
    """Password -> scrypt key; fresh random salt and IV every call."""
    salt = os.urandom(SALT_LEN)
    iv = os.urandom(IV_LEN)

    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded = padder.update(message) + padder.finalize()

    enc = Cipher(algorithms.AES(_derive_key(password, salt)), modes.CBC(iv)).encryptor()
    return salt + iv + enc.update(padded) + enc.finalize()


def _decrypt(blob: bytes, password: str) -> bytes:
    block = algorithms.AES.block_size // 8
    body = len(blob) - SALT_LEN - IV_LEN
    if body < block or body % block:
        raise ValueError("No valid hidden data (corrupted or not a stego image)")

    salt, iv, ciphertext = blob[:SALT_LEN], blob[SALT_LEN : SALT_LEN + IV_LEN], blob[SALT_LEN + IV_LEN :]
    dec = Cipher(algorithms.AES(_derive_key(password, salt)), modes.CBC(iv)).decryptor()
    padded = dec.update(ciphertext) + dec.finalize()

    try:
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        return unpadder.update(padded) + unpadder.finalize()
    except ValueError:
        raise ValueError("Wrong password or corrupted data") from None


# ---------- JPG ----------
def jpg_usable_indices(Y):
    mask = np.abs(Y) >= 2
    mask[..., 0, 0] = False
    return np.flatnonzero(mask.ravel())


def jpg_embed(src, dst, message: bytes, password: str):
    """Encrypt `message` with AES-CBC (key from `password`), then hide the ciphertext."""
    message = _encrypt(message, password)

    im = jpeglib.read_dct(src)
    Y = im.Y.copy()
    idx = jpg_usable_indices(Y)

    payload = len(message).to_bytes(4, "big") + message
    bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8))
    if len(bits) > len(idx):
        raise ValueError(f"Too big: {len(bits)} bits, capacity {len(idx)}")

    flat = Y.ravel()
    chosen = idx[: len(bits)]
    vals = flat[chosen]
    mag = (np.abs(vals) & ~1) | bits
    flat[chosen] = np.sign(vals) * mag

    im.Y[...] = flat.reshape(Y.shape)
    im.write_dct(dst)


def jpg_extract(src, password: str) -> bytes:
    """Read the hidden ciphertext and decrypt it with `password`. `src` must be a file path."""
    im = jpeglib.read_dct(src)
    flat = im.Y.ravel()
    idx = jpg_usable_indices(im.Y)

    def read_bits(start, n):
        return (np.abs(flat[idx[start : start + n]]) & 1).astype(np.uint8)

    if len(idx) < 32:
        raise ValueError("No hidden data (image too small)")
    length = int.from_bytes(np.packbits(read_bits(0, 32)).tobytes(), "big")
    if 32 + length * 8 > len(idx):
        raise ValueError("No hidden data (or corrupted length header)")

    blob = np.packbits(read_bits(32, length * 8)).tobytes()
    return _decrypt(blob, password)


# ---------- PNG ----------
def png_embed(src, dst, data: bytes, password: str):
    """Encrypt `data` with AES-CBC (key from `password`), then hide the ciphertext."""
    data = _encrypt(data, password)

    arr = np.array(Image.open(src).convert("RGB"))
    flat = arr.flatten()

    payload = len(data).to_bytes(4, "big") + data
    bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8))
    if len(bits) > flat.size:
        raise ValueError(f"Too big: {len(bits)} bits, capacity {flat.size}")

    flat[: len(bits)] = (flat[: len(bits)] & 0xFE) | bits
    Image.fromarray(flat.reshape(arr.shape)).save(dst, format="PNG")


def png_extract(src, password: str) -> bytes:
    """Read the hidden ciphertext and decrypt it with `password`."""
    flat = np.array(Image.open(src).convert("RGB")).ravel()

    length = int.from_bytes(np.packbits(flat[:32] & 1).tobytes(), "big")
    if 32 + length * 8 > flat.size:
        raise ValueError("No hidden data (or corrupted length header)")

    blob = np.packbits(flat[32 : 32 + length * 8] & 1).tobytes()
    return _decrypt(blob, password)


# ---------- bytes in -> bytes out wrappers ----------
def embed_png_bytes(data: bytes, message: bytes, password: str) -> bytes:
    out = io.BytesIO()
    png_embed(io.BytesIO(data), out, message, password)  # PIL accepts file-like objects
    return out.getvalue()


def embed_jpg_bytes(data: bytes, message: bytes, password: str) -> bytes:
    # jpeglib needs real file paths, so use a temp directory
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "in.jpg")
        dst = os.path.join(tmp, "out.jpg")

        with open(src, "wb") as f:
            f.write(data)

        jpg_embed(src, dst, message, password)
        with open(dst, "rb") as f:
            return f.read()