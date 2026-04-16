import hashlib
import re
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from src.core.db import get_connection, init_db

router = APIRouter(prefix="/auth", tags=["auth"])

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")
init_db()


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class UserResponse(BaseModel):
    username: str


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _validate_credentials(username: str, password: str):
    if not USERNAME_PATTERN.fullmatch(username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Username must be 3-32 characters and use only letters, "
                "numbers, dot, underscore, or hyphen."
            ),
        )

    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long.",
        )
    if not any(ch.isdigit() for ch in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one number.",
        )
    if not any(ch.isalpha() for ch in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one letter.",
        )


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme",
        )

    token = authorization[len(prefix) :].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    return token


def get_current_user(authorization: str | None = Header(default=None)) -> str:
    token = _extract_bearer_token(authorization)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT username FROM auth_tokens WHERE token = ?",
            (token,),
        ).fetchone()
    username = row["username"] if row else None
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return username


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest):
    username = payload.username.strip().lower()
    password = payload.password.strip()
    _validate_credentials(username, password)

    with get_connection() as conn:
        existing_user = conn.execute(
            "SELECT username FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists",
            )

        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, _hash_password(password)),
        )
        conn.commit()

    token = secrets.token_urlsafe(32)
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO auth_tokens (token, username) VALUES (?, ?)",
            (token, username),
        )
        conn.commit()
    return AuthResponse(access_token=token, username=username)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    username = payload.username.strip().lower()
    password = payload.password.strip()
    _validate_credentials(username, password)

    with get_connection() as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    stored_password_hash = row[0] if row else None

    if not stored_password_hash or stored_password_hash != _hash_password(password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = secrets.token_urlsafe(32)
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO auth_tokens (token, username) VALUES (?, ?)",
            (token, username),
        )
        conn.commit()
    return AuthResponse(access_token=token, username=username)


@router.get("/me", response_model=UserResponse)
def me(username: str = Depends(get_current_user)):
    return UserResponse(username=username)


@router.post("/logout")
def logout(authorization: str | None = Header(default=None)):
    token = _extract_bearer_token(authorization)
    with get_connection() as conn:
        conn.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
        conn.commit()
    return {"status": "logged_out"}
