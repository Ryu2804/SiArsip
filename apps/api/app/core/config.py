import base64
import os 
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
BUCKET_NAME = os.getenv("BUCKET_NAME")
SECRET_KEY = os.getenv("SECRET_KEY")
AWS_ENDPOINT_URL_S3 = os.getenv("AWS_ENDPOINT_URL_S3")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION_NAME = os.getenv("AWS_REGION_NAME")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

def get_master_key() -> bytes:
    raw = os.getenv("MASTER_KEY")
    if not raw:
        raise RuntimeError("MASTER_KEY tidak ditemukan di environment variable")
    
    try:
        key = base64.b64decode(raw)
    except Exception:
        raise RuntimeError("MASTER_KEY harus berupa string base64 yang valid")
        
    if len(key) != 32:
        raise RuntimeError(f"MASTER_KEY harus tepat 32 byte (256-bit), terbaca {len(key)} byte")
        
    return key