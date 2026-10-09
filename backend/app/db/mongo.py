"""MongoDB connection management using Motor (async driver).

A single AsyncIOMotorClient is created at startup and shared across requests.
Collections are exposed via helper accessors so routes never hardcode names.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings


class MongoManager:
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None


mongo = MongoManager()


async def connect_to_mongo() -> None:
    """Open the Mongo client. Called on FastAPI startup."""
    settings = get_settings()
    mongo.client = AsyncIOMotorClient(settings.mongo_uri)
    mongo.db = mongo.client[settings.mongo_db_name]
    # Ensure indexes (idempotent).
    await mongo.db["users"].create_index("username", unique=True)
    await mongo.db["users"].create_index("email", unique=True, sparse=True)
    await mongo.db["documents"].create_index("owner")
    await mongo.db["interactions"].create_index("owner")


async def close_mongo_connection() -> None:
    """Close the Mongo client. Called on FastAPI shutdown."""
    if mongo.client is not None:
        mongo.client.close()


def get_db() -> AsyncIOMotorDatabase:
    """Return the active database handle (raises if not connected)."""
    if mongo.db is None:
        raise RuntimeError("MongoDB is not connected. Did startup run?")
    return mongo.db


# --- Collection accessors ---
def users_collection():
    return get_db()["users"]


def profiles_collection():
    return get_db()["learner_profiles"]


def documents_collection():
    return get_db()["documents"]


def interactions_collection():
    return get_db()["interactions"]
