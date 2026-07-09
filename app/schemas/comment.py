from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    text: str = Field(..., min_length=1)


class CommentUpdate(BaseModel):
    text: Optional[str] = Field(default=None, min_length=1)


class CommentRead(BaseModel):
    id: int
    text: str
    task_id: int
    author_id: int = Field(validation_alias="user_id")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
