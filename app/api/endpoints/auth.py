from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.crud.user import create_user, get_user_by_email
from app.db.session import get_db
from app.schemas.auth import AccessTokenResponse, RefreshTokenRequest, Token
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["Authentication"])

SessionDep = Annotated[AsyncSession, Depends(get_db)]
OAuth2FormDep = Annotated[OAuth2PasswordRequestForm, Depends()]


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    session: SessionDep,
):
    existing_user = await get_user_by_email(session, user_in.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    user = await create_user(session, user_in)
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2FormDep,
    session: SessionDep,
):
    user = await get_user_by_email(session, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(subject=user.email)
    refresh_token = create_refresh_token(subject=user.email)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(
    body: RefreshTokenRequest,
    session: SessionDep,
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(body.refresh_token)
    except JWTError as exc:
        raise credentials_exception from exc

    if payload.get("type") != TOKEN_TYPE_REFRESH:
        raise credentials_exception

    email = payload.get("sub")
    if not email:
        raise credentials_exception

    user = await get_user_by_email(session, email)
    if user is None:
        raise credentials_exception

    access_token = create_access_token(subject=user.email)
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    return Response(status_code=status.HTTP_204_NO_CONTENT)
