class CryptoError(Exception):
    """Base exception untuk seluruh operasi Kriptografi."""
    pass

class InvalidContainerError(CryptoError):
    """Magic header atau Cipher ID rusak/tidak dikenal."""
    pass

class IntegrityError(CryptoError):
    """Tag Autentikasi atau HMAC Gagal diverifikasi (Data Termanipulasi)"""