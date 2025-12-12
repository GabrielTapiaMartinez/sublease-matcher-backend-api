from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from ..adapters.sqlalchemy import models
from ..dependencies.uow import get_uow
from ..interfaces.uow import UnitOfWork

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()


# Schemas
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    firstName: str | None = None
    lastName: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    user: UserDTO


class UserDTO(BaseModel):
    id: str
    email: str
    firstName: str | None
    lastName: str | None
    role: str | None
    show_in_swipe: bool | None = True
    email_notifications_enabled: bool | None = True


# Helpers
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def create_session(user_id: str, uow: UnitOfWork) -> str:
    token = uow.sessions.create(user_id)
    uow.commit()
    return token


# Routes
@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, uow: UnitOfWork = Depends(get_uow)):
    # check if user exists
    existing = uow.users.get_by_email(payload.email)

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User with this email already exists"
        )

    # create user
    user_id = f"user-{secrets.token_hex(4)}"
    new_user = uow.users.create(
        user_id=user_id,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        first_name=payload.firstName,
        last_name=payload.lastName,
    )
    # uow.session.add(new_user) # Handled by repo now

    # generate token
    token = create_session(user_id, uow)

    return AuthResponse(
        token=token,
        user=UserDTO(
            id=user_id,
            email=new_user.email,
            firstName=new_user.first_name,
            lastName=new_user.last_name,
            role=None,
            show_in_swipe=new_user.show_in_swipe,
            email_notifications_enabled=new_user.email_notifications_enabled,
        ),
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, uow: UnitOfWork = Depends(get_uow)):
    user = uow.users.get_by_email(payload.email)

    if (
        not user
        or not user.password_hash
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_session(user.id, uow)

    return AuthResponse(
        token=token,
        user=UserDTO(
            id=user.id,
            email=user.email,
            firstName=user.first_name,
            lastName=user.last_name,
            role=user.current_role,
            show_in_swipe=user.show_in_swipe,
            email_notifications_enabled=user.email_notifications_enabled,
        ),
    )


@router.post("/logout")
def logout(creds: HTTPBearer = Depends(security), uow: UnitOfWork = Depends(get_uow)):
    # This naive implementation just tries to delete the session if it exists
    # A cleaner way requires extracting the token from the request properly via dependency
    token = creds.credentials
    uow.sessions.delete(token)
    uow.commit()
    return {"message": "Logged out"}
