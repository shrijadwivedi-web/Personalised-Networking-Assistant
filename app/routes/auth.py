"""
Auth Router
-------------
Two endpoints:
  - POST /auth/register  -> create a new user account
  - POST /auth/login     -> verify credentials, issue a JWT access token

Passwords are never stored in plaintext -- only bcrypt hashes are persisted.
Login uses a generic "Incorrect username or password" error for both the
"user doesn't exist" and "wrong password" cases, so the API doesn't leak
which usernames are registered (a standard security practice -- it
prevents username enumeration).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.database import get_db
from app.db_models import User
from app.models import TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(request: UserRegisterRequest, db: Session = Depends(get_db)) -> User:
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with that username already exists",
        )

    user = User(username=request.username, hashed_password=hash_password(request.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(request: UserLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.username == request.username).first()

    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token = create_access_token(subject=user.username)
    return TokenResponse(access_token=access_token)
