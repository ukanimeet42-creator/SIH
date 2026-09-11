"""
VoxGuard Engine — FastAPI Application Entry Point

Sets up CORS, routers, lifespan hooks, and a health-check endpoint.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_telemetry import router as telemetry_router
from app.api.websocket_audio import router as ws_router
from app.core.config import get_settings
from app.services.detector_engine import DetectorEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)
_settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialise detector engine on startup."""
    logger.info("═══ VoxGuard Engine v%s starting ═══", _settings.APP_VERSION)

    # Pre-initialise the detector engine (loads ONNX model if configured)
    engine = DetectorEngine()
    await engine.initialise()

    logger.info("═══ VoxGuard Engine ready ═══")
    yield
    logger.info("═══ VoxGuard Engine shutting down ═══")


app = FastAPI(
    title=_settings.APP_NAME,
    version=_settings.APP_VERSION,
    description=(
        "Real-Time Voice Cloning Detection & Active Prevention Engine. "
        "Analyses live audio streams for synthetic voice artefacts using "
        "deterministic DSP heuristics and optional ONNX model inference."
    ),
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────
app.include_router(ws_router)
app.include_router(telemetry_router)


# ── Health Check ─────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health_check():
    """System health endpoint."""
    return {
        "status": "healthy",
        "engine": _settings.APP_NAME,
        "version": _settings.APP_VERSION,
        "mode": "ONNX + DSP" if _settings.USE_ONNX else "DSP heuristic",
    }


@app.get("/", tags=["system"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": _settings.APP_NAME,
        "version": _settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "websocket": "/ws/live-stream/{session_id}",
    }
