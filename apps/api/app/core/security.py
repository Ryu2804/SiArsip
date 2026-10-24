from pwdlib import PasswordHash
from app.core.config import SECRET_KEY, ALGORITHM
import jwt
from datetime import datetime, timedelta

password_hash = PasswordHash.recommended()

ACCESS_TOKEN_EXPIRE_MINUTES = 60  

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)

def generate_jwt_token(user_id: str) -> str:
    now = datetime.utcnow()
    payload = {
        "user_id": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=str(ALGORITHM))
    return token

def decode_jwt_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=str(ALGORITHM), options={"require": ["sub", "exp", "iat"]})
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception("Token has expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid token")