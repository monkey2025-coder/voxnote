from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------- Auth ----------

class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Project ----------

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class ProjectUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class ProjectResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime
    note_count: int = 0

    class Config:
        from_attributes = True


# ---------- Note ----------

class NoteUpdate(BaseModel):
    text: Optional[str] = None
    project_id: Optional[int] = None
    sort_order: Optional[int] = None


class NoteResponse(BaseModel):
    id: int
    project_id: Optional[int]
    audio_url: str
    text: str
    duration: float
    sort_order: int
    recorded_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------- Annotation ----------

class AnnotationCreate(BaseModel):
    type: str = Field(pattern="^(text|image)$")
    content: str = Field(min_length=1)


class AnnotationResponse(BaseModel):
    id: int
    note_id: int
    type: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class NoteWithAnnotations(NoteResponse):
    annotations: list[AnnotationResponse] = []
