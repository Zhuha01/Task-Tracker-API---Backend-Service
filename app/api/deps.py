"""FastAPI dependencies for authentication."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import ALGORITHM
from app.crud.user import get_user_by_email
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

TokenDep = Annotated[str, Depends(oauth2_scheme)]
SessionDep = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(token: TokenDep, session: SessionDep):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise credentials_exception from exc

    email = payload.get("sub")
    if not email:
        raise credentials_exception

    user = await get_user_by_email(session, email)
    if user is None:
        raise credentials_exception

    return user
