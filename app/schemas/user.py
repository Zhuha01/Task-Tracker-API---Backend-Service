from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import Role


class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=50, description="User name")


class UserCreate(UserBase):
    password: str = Field(
        ..., min_length=8, description="Password (minimum 8 characters)"
    )


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = Field(
        default=None, min_length=2, max_length=50, description="User name"
    )
    password: Optional[str] = Field(
        default=None, min_length=8, description="Password (minimum 8 characters)"
    )
    role: Optional[Role] = None


class UserRead(UserBase):
    id: int
    role: Role
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
