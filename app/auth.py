"""
Authentication Utilities
---------------------------
Password hashing via passlib (bcrypt) and stateless JWT access tokens via
python-jose. JWTs are used rather than server-side sessions because they
keep the API stateless -- any backend instance can verify a token without
needing shared session storage, which matters if this is ever scaled
horizontally or containerized (see docker-compose.yml).

SECRET_KEY MUST be overridden via the SECRET_KEY environment variable in
any real deployment. The default below is only safe for local development
and is intentionally obvious so it's never mistaken for a real secret.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY = os.getenv("SECRET_KEY", "INSECURE-DEV-ONLY-CHANGE-ME")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject: The token subject, typically the username. Stored in the
            'sub' claim.
        expires_minutes: Optional override for token lifetime; defaults to
            ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        The encoded JWT as a string.
    """
    expire_delta = timedelta(minutes=expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES)
    expire_at = datetime.now(timezone.utc) + expire_delta

    payload = {"sub": subject, "exp": expire_at}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    """
    Decode and validate a JWT access token.

    Returns:
        The subject (username) if the token is valid and not expired,
        otherwise None.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
