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