"""
app/main.py
───────────
FastAPI application entry point.

This file:
  1. Creates the FastAPI app instance with metadata.
  2. Registers API routers (added per phase).
  3. Adds a lifespan handler — runs startup/shutdown logic cleanly.
  4. Adds a root health-check endpoint so we can immediately verify the server is up.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


# ── Lifespan ──────────────────────────────────────────────────────────────────
# In FastAPI, lifespan replaces the old @app.on_event("startup") pattern.
# Everything before `yield` runs on startup; after `yield` runs on shutdown.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    print(f"🚀  Nerve starting up  [env={settings.app_env}]")
    yield
    # SHUTDOWN
    print("🛑  Nerve shutting down")


# ── App instance ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Nerve API",
    description="The Autonomous SRE Engine — from production crash to merged PR.",
    version="0.1.0",
    docs_url="/docs",        # Swagger UI
    redoc_url="/redoc",      # ReDoc UI
    lifespan=lifespan,
)


# ── CORS middleware ───────────────────────────────────────────────────────────
# Allows the Next.js frontend (localhost:3000) to call our API in dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"] if settings.app_env == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["meta"])
async def health_check():
    """
    Simple liveness probe.
    Returns 200 OK so load balancers / Docker healthchecks know the app is alive.
    """
    return {"status": "ok", "env": settings.app_env}


# ── Routers ───────────────────────────────────────────────────────────────────
# We'll register phase-specific routers here as we build them.
# Example (Phase 1D/1E):
#   from app.api.v1 import ingest, events
#   app.include_router(ingest.router, prefix="/api/v1", tags=["ingest"])
#   app.include_router(events.router, prefix="/api/v1", tags=["events"])
