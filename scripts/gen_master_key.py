import base64
import secrets

if __name__ == "__main__":
    key = secrets.token_bytes(32)
    print(base64.b64encode(key).decode("utf-8"))