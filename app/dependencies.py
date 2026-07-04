"""
Auth Dependency
-----------------
Provides get_current_user, a FastAPI dependency that extracts the bearer
token from the Authorization header, validates it, and loads the
corresponding User from the database. Any route that depends on this is
automatically protected -- requests without a valid token receive a 401
before the route handler body ever runs.

Note on OAuth2PasswordBearer: it's used here purely as a convenient way to
extract and validate "Authorization: Bearer <token>" headers, NOT to
enforce the full OAuth2 password-grant flow. Our actual /auth/login
endpoint accepts a plain JSON body (UserLoginRequest), not OAuth2's
required form-encoded username/password fields. One consequence: the
"Authorize" button in the auto-generated Swagger UI at /docs expects
form-encoded credentials and will not work against our JSON login endpoint.
To try protected endpoints interactively, log in via POST /auth/login
(e.g. with curl or the Streamlit frontend) and paste the resulting token
into Swagger's Authorize dialog directly instead.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth import decode_access_token
from app.database import get_db
from app.db_models import User

# tokenUrl points at the login endpoint; this only affects the auto-generated
# Swagger UI's "Authorize" button, not runtime behavior.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    username = decode_access_token(token)
    if username is None:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception

    return user
