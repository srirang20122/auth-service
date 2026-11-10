import sqlite3
import time
from datetime import datetime, timezone

import jwt
from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prometheus_client import Counter
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, EmailStr, Field

from . import config
from .db import db, init_db
from .security import create_token, decode_token, hash_password, verify_password

init_db()

app = FastAPI(title="Auth Service", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
bearer = HTTPBearer(auto_error=False)

# Business metrics for the Grafana dashboard (exposed on /metrics).
LOGINS = Counter("auth_login_total", "Login attempts", ["result"])          # success | failed
REGISTRATIONS = Counter("auth_register_total", "Registrations", ["result"])  # success | duplicate
LOGOUTS = Counter("auth_logout_total", "Logouts")
for _r in ("success", "failed"):
    LOGINS.labels(result=_r)
for _r in ("success", "duplicate"):
    REGISTRATIONS.labels(result=_r)
UNAUTHORIZED = HTTPException(
    status.HTTP_401_UNAUTHORIZED,
    "Invalid or expired token",
    headers={"WWW-Authenticate": "Bearer"},
)


# ---------- schemas ----------
class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    full_name: str
    email: str
    created_at: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ---------- auth dependency ----------
def current_claims(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if creds is None or creds.scheme.lower() != "bearer":
        raise UNAUTHORIZED
    try:
        claims = decode_token(creds.credentials)
    except jwt.PyJWTError:
        raise UNAUTHORIZED
    with db() as conn:
        revoked = conn.execute(
            "SELECT 1 FROM revoked_tokens WHERE jti = ?", (claims["jti"],)
        ).fetchone()
    if revoked:
        raise UNAUTHORIZED
    return claims


def current_user(claims: dict = Depends(current_claims)) -> sqlite3.Row:
    with db() as conn:
        user = conn.execute(
            "SELECT id, full_name, email, created_at FROM users WHERE id = ?",
            (int(claims["sub"]),),
        ).fetchone()
    if user is None:
        raise UNAUTHORIZED
    return user


# ---------- routes ----------
@app.get("/health", tags=["system"])
def health():
    with db() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok"}


@app.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED, tags=["auth"])
def register(body: RegisterIn):
    email = body.email.lower()
    now = datetime.now(timezone.utc).isoformat()
    try:
        with db() as conn:
            cur = conn.execute(
                "INSERT INTO users (full_name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (body.full_name.strip(), email, hash_password(body.password), now),
            )
            user_id = cur.lastrowid
    except sqlite3.IntegrityError:
        REGISTRATIONS.labels(result="duplicate").inc()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    REGISTRATIONS.labels(result="success").inc()
    return UserOut(id=user_id, full_name=body.full_name.strip(), email=email, created_at=now)


@app.post("/auth/login", response_model=TokenOut, tags=["auth"])
def login(body: LoginIn):
    with db() as conn:
        user = conn.execute(
            "SELECT id, password_hash FROM users WHERE email = ?", (body.email.lower(),)
        ).fetchone()
    if user is None or not verify_password(body.password, user["password_hash"]):
        LOGINS.labels(result="failed").inc()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    LOGINS.labels(result="success").inc()
    token, expires_in = create_token(user["id"])
    return TokenOut(access_token=token, expires_in=expires_in)


@app.get("/auth/me", response_model=UserOut, tags=["auth"])
def me(user: sqlite3.Row = Depends(current_user)):
    return UserOut(**dict(user))


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, tags=["auth"])
def logout(claims: dict = Depends(current_claims)):
    """Revoke this token so it can no longer be used, even before it expires."""
    now = int(time.time())
    with db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO revoked_tokens (jti, expires_at) VALUES (?, ?)",
            (claims["jti"], int(claims["exp"])),
        )
        conn.execute("DELETE FROM revoked_tokens WHERE expires_at < ?", (now,))
    LOGOUTS.inc()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


Instrumentator(excluded_handlers=["/health", "/metrics"]).instrument(app).expose(app, include_in_schema=False)
