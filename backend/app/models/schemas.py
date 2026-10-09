"""Pydantic schemas for request/response bodies and stored documents.

These describe the shapes used by the API and (loosely) the MongoDB documents.
MongoDB is schema-flexible, so these models are the enforced contract at the edge.
"""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


# --- Auth ---
class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    email: EmailStr | None = None
    full_name: str | None = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserPublic(BaseModel):
    """User info safe to return to the client (no password hash)."""
    username: str
    email: EmailStr | None = None
    full_name: str | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


# --- Learner profile ---
class Level(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class Framework(str, Enum):
    STAR = "star"
    DESIGN_THINKING = "design_thinking"
    SCAFFOLDING = "scaffolding"


class LearnerProfile(BaseModel):
    username: str
    level: Level = Level.INTERMEDIATE
    preferred_style: str = "analogy"   # analogy | clinical | concise
    topic_scores: dict[str, float] = Field(default_factory=dict)


# --- Documents ---
class DocumentPublic(BaseModel):
    doc_id: str
    filename: str
    owner: str
    status: str
    size_bytes: int
    chunks_indexed: int = 0
    uploaded_at: datetime


# --- Query (RAG) ---
class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    topic: str | None = None
    level: Level | None = None          # optional override of the profile level
    framework: Framework = Framework.STAR


class Citation(BaseModel):
    source: str
    page: int | None = None
    chunk_id: str | None = None


class QueryResponse(BaseModel):
    answer: str
    level: Level
    framework: Framework
    citations: list[Citation] = Field(default_factory=list)
    trace_id: str
    stubbed: bool = True                # flips to False when real RAG is wired in
