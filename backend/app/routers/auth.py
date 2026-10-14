from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    authenticate_user,
    ensure_supported_registration_role,
    get_current_user,
    hash_password,
    issue_access_token,
    issue_tokens,
    normalize_email,
    revoke_refresh_session,
    rotate_refresh_session,
)
from app.db import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


def user_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        role=user.role,
        created_at=user.created_at,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    role = ensure_supported_registration_role(payload.role)
    email = normalize_email(payload.email)
    if db.scalar(
        select(User).where(or_(User.email == email, User.username == payload.username))
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username is already registered",
        )

    user = User(
        email=email,
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=role,
    )
    db.add(user)
    try:
        db.flush()
        access_token, refresh_token = issue_tokens(db, user)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username is already registered",
        ) from exc
    db.refresh(user)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_response(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(db, payload.identifier, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token, refresh_token = issue_tokens(db, user)
    db.commit()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_response(user),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user, refresh_token = rotate_refresh_session(db, payload.refresh_token)
    access_token = issue_access_token(user)
    db.commit()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_response(user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: LogoutRequest, db: Session = Depends(get_db)) -> None:
    revoke_refresh_session(db, payload.refresh_token)
    db.commit()


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return user_response(current_user)
