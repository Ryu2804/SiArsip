import os
import pytest
from app.services.crypto.envelope import wrap_key, unwrap_key
from app.services.crypto.exceptions import IntegrityError

def test_envelope_round_trip():
    mk = os.urandom(32)
    dek = os.urandom(32)  # kunci per-file
    wrapped = wrap_key(dek, master_key=mk)
    unwrapped = unwrap_key(wrapped, master_key=mk)
    assert unwrapped == dek

def test_unwrap_wrong_master_key_fails():
    mk1 = os.urandom(32)
    mk2 = os.urandom(32)
    dek = os.urandom(32)
    wrapped = wrap_key(dek, master_key=mk1)
    
    with pytest.raises(IntegrityError):
        unwrap_key(wrapped, master_key=mk2)

def test_unwrap_tampered_wrapped_key_fails():
    mk = os.urandom(32)
    dek = os.urandom(32)
    wrapped = bytearray(wrap_key(dek, master_key=mk))
    wrapped[-1] ^= 0x01
    
    with pytest.raises(IntegrityError):
        unwrap_key(bytes(wrapped), master_key=mk)