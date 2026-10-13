"""FastAPI application entrypoint.

Exposes an app factory (`create_app`) and a module-level `app` instance so the
service can be started with `uvicorn app.main:app`. The MongoDB connection is
opened on startup and closed on shutdown via the lifespan context manager.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.mongo import connect_to_mongo, close_mongo_connection

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the Mongo connection on startup; close it on shutdown.

    Index creation in `connect_to_mongo` is idempotent, so repeated startups
    are safe.
    """
    logger.info("Starting up: connecting to MongoDB...")
    await connect_to_mongo()
    logger.info("MongoDB connected.")
    try:
        yield
    finally:
        logger.info("Shutting down: closing MongoDB connection...")
        await close_mongo_connection()
        logger.info("MongoDB connection closed.")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Personalized Learning RAG Assistant",
        description="Grounded, personalized, framework-structured exam-prep assistant.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers are registered in later stories (health, auth, ingest, query).

    return app


app = create_app()
