"""
AI Interview Agent — FastAPI application entry point.

Starts the app, registers CORS middleware, includes the interview router,
and verifies that the curriculum and candidate data loads correctly at
startup.

Run with:
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import sys

# Python 3.11+ is required for match statements used in later tasks.
if sys.version_info < (3, 11):
    raise RuntimeError(
        f"Python 3.11 or newer is required. You are running {sys.version}."
    )

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Trigger data load at startup — raises FileNotFoundError early if data is missing.
from data.loader import candidates, curriculum_by_day  # noqa: F401
from routers.interview import router as interview_router

app = FastAPI(
    title="AI Interview Agent",
    description="Personalised technical interview agent powered by LLMs.",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS — allow the Vite dev server (port 5173) and any production origin.
# Expand allow_origins for production deployment.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(interview_router)


# ---------------------------------------------------------------------------
# Health check — useful for smoke tests and deployment probes.
# ---------------------------------------------------------------------------
@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "candidates_loaded": len(candidates),
        "curriculum_days_loaded": len(curriculum_by_day),
    }
