# backend/app/main.py
"""
KiranaLens v3.0 — FastAPI Application Entry Point.
Visual Credit Bureau for India's Kirana Economy.
CRP TenzorX 2026 | Poonawalla Fincorp National AI Hackathon.
"""

import logging
import os
import sys
import io
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("kiranalens")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info("="*60)
    logger.info("KiranaLens v4.0 Starting...")
    logger.info("="*60)

    # Pre-load YOLOv8 model
    try:
        from app.services.vision_service import _get_model
        _get_model()
        logger.info("[OK] YOLOv8 model loaded")
    except Exception as e:
        logger.warning(f"[WARN] YOLOv8 pre-load failed (will retry on first request): {e}")

    # Check HF token
    hf_token = os.getenv("HF_TOKEN", "")
    if hf_token and "your_token" not in hf_token:
        logger.info(f"[OK] HF_TOKEN found: {hf_token[:8]}...{hf_token[-4:]}")
    else:
        logger.warning("[WARN] HF_TOKEN not set -- LLM features will use fallback mode")
        logger.info("       Set HF_TOKEN in .env -> https://huggingface.co/settings/tokens")

    logger.info("[OK] Backend ready at http://localhost:8000")
    logger.info("[OK] API docs at http://localhost:8000/docs")
    logger.info("[OK] Demo endpoint: GET /api/v1/demo")
    logger.info("="*60)

    yield

    logger.info("KiranaLens shutting down...")


app = FastAPI(
    title="KiranaLens v4.0",
    description="Visual Credit Bureau for India's Kirana Economy",
    version="4.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Register routes
from app.routes.assessment import router as assessment_router
app.include_router(assessment_router, prefix="/api/v1")
