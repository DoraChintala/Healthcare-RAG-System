"""Health check endpoint.

Reports whether the service and its dependencies are reachable so that
Docker, load balancers, and CI smoke tests can gate traffic on it.
"""
from fastapi import APIRouter

from app.core.config import get_settings
from app.db.mongo import mongo

router = APIRouter(tags=["health"])


async def _ping_mongo() -> bool:
    """Return True if MongoDB responds to a ping, else False."""
    if mongo.client is None:
        return False
    try:
        await mongo.client.admin.command("ping")
        return True
    except Exception:
        return False


@router.get("/api/health")
async def health() -> dict:
    """Liveness/readiness probe.

    Returns overall status plus the state of the vector store (MongoDB Atlas)
    and the configured LLM provider. Never raises: a down dependency is
    reported as degraded rather than a 500.
    """
    settings = get_settings()
    mongo_up = await _ping_mongo()
    return {
        "status": "ok" if mongo_up else "degraded",
        "vector_store": "up" if mongo_up else "down",
        "provider": settings.llm_provider,
    }
