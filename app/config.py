import os

SECRET_KEY = os.environ.get("SECRET_KEY", "")
if len(SECRET_KEY) < 32:
    raise RuntimeError("SECRET_KEY must be set to 32+ random characters")

DB_PATH = os.environ.get("DB_PATH", "data/auth.db")
TOKEN_EXPIRE_MINUTES = int(os.environ.get("TOKEN_EXPIRE_MINUTES", "60"))
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "http://localhost:4200").split(",")
    if o.strip()
]
ALGORITHM = "HS256"
PBKDF2_ITERATIONS = 200_000
