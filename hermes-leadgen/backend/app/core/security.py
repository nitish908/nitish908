"""Password hashing, JWT issuance/verification, and provider-credential encryption.

Credentials for lead-source/AI providers are encrypted at rest with Fernet
using CREDENTIALS_ENCRYPTION_KEY (generate with
`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from cryptography.fernet import Fernet, InvalidToken
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(subject: str, role: str) -> str:
    if not settings.secret_key:
        raise RuntimeError("SECRET_KEY is not configured; refusing to issue tokens")
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None


def _fernet() -> Fernet:
    if not settings.credentials_encryption_key:
        raise RuntimeError("CREDENTIALS_ENCRYPTION_KEY is not configured; refusing to handle provider credentials")
    return Fernet(settings.credentials_encryption_key.encode())


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(token: str) -> Optional[str]:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return None
