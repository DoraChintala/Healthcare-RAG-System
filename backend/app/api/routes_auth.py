"""Authentication routes: registration (and login in a later story)."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.auth.security import hash_password
from app.db.mongo import users_collection
from app.models.schemas import UserPublic, UserRegister

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
)
async def register(payload: UserRegister) -> UserPublic:
    """Create a new user.

    The password is stored only as a bcrypt hash. Duplicate username or email
    is rejected with 409. The response never includes the password hash.
    """
    users = users_collection()

    # Proactive duplicate check for a clear error message.
    dup_query: dict = {"$or": [{"username": payload.username}]}
    if payload.email is not None:
        dup_query["$or"].append({"email": payload.email})
    if await users.find_one(dup_query):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered",
        )

    doc = {
        "username": payload.username,
        "email": payload.email,
        "full_name": payload.full_name,
        "password_hash": hash_password(payload.password),
        "created_at": datetime.now(timezone.utc),
    }

    try:
        await users.insert_one(doc)
    except DuplicateKeyError:
        # Safety net against a race between the check above and insert.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered",
        )

    return UserPublic(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
    )
