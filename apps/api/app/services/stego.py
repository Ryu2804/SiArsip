import io
import os
import tempfile

import jpeglib
import numpy as np
from PIL import Image


def detect_image_type(data: bytes) -> str | None:
    """Detect by magic bytes, not by filename or client-supplied content type."""
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    return None


# ---------- JPG (your code, unchanged) ----------
def jpg_usable_indices(Y):
    mask = np.abs(Y) >= 2
    mask[..., 0, 0] = False
    return np.flatnonzero(mask.ravel())


def jpg_embed(src, dst, message: bytes):
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


# ---------- PNG (your code, unchanged) ----------
def png_embed(src, dst, data: bytes):
    arr = np.array(Image.open(src).convert("RGB"))
    flat = arr.flatten()

    payload = len(data).to_bytes(4, "big") + data
    bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8))
    if len(bits) > flat.size:
        raise ValueError(f"Too big: {len(bits)} bits, capacity {flat.size}")

    flat[: len(bits)] = (flat[: len(bits)] & 0xFE) | bits
    Image.fromarray(flat.reshape(arr.shape)).save(dst, format="PNG")


# ---------- bytes in -> bytes out wrappers ----------
def embed_png_bytes(data: bytes, message: bytes) -> bytes:
    out = io.BytesIO()
    png_embed(io.BytesIO(data), out, message)   # PIL accepts file-like objects
    return out.getvalue()


def embed_jpg_bytes(data: bytes, message: bytes) -> bytes:
    # jpeglib needs real file paths, so use a temp directory
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "in.jpg")
        dst = os.path.join(tmp, "out.jpg")
        
        with open(src, "wb") as f:
            f.write(data)

        jpg_embed(src, dst, message)
        with open(dst, "rb") as f:
            return f.read()