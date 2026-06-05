"""
FastAPI application entry point.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, documents, followup, leads, settings as settings_router
from app.core.config import get_settings
from app.core.security import router as auth_router
from app.db.session import init_db
from app.scheduler.followup_scheduler import (
    reload_pending_followup_jobs,
    shutdown_scheduler,
    start_scheduler,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="AMD Chatbot API",
    description="Backend API cho AMD AI Solutions Website Chatbot",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────
app.include_router(auth_router)
app.include_router(chat.router)
app.include_router(leads.router)
app.include_router(documents.router)
app.include_router(followup.router)
app.include_router(settings_router.router)


# ── Lifecycle ─────────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
    logger.info("Starting AMD Chatbot API...")
    await init_db()
    start_scheduler()
    reloaded = await reload_pending_followup_jobs()
    logger.info(f"Reloaded {reloaded} pending follow-up jobs")
    logger.info("Ready ✓")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    shutdown_scheduler()
    logger.info("Shutdown complete")


# ── Health check ──────────────────────────────
@app.get("/health", tags=["System"])
async def health() -> dict:
    return {"status": "ok", "version": "1.0.0"}
