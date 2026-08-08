"""
Pydantic request/response schemas for POST /api/interview.

These match the API contract in docs/technical-spec.md exactly.
The three state-tracking fields (total_questions_asked, topics_completed,
days_covered) are included as optional display fields in the response —
they do not break the spec contract but power the frontend progress UI.
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sub-models for the candidate object (mirrors candidates.json schema)
# ---------------------------------------------------------------------------

class CandidateMember(BaseModel):
    id: str
    name: str
    jobRole: str
    yearsExperience: int
    education: str
    status: str


class CandidateMission(BaseModel):
    day: int
    title: str
    passed: Optional[bool] = None
    attempts: Optional[int] = None
    skipped: Optional[bool] = None


class CandidateSignals(BaseModel):
    commitDays: int
    missionsCompleted: int
    missionsFirstTry: int


class Candidate(BaseModel):
    member: CandidateMember
    missions: list[CandidateMission]
    signals: CandidateSignals


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

class InterviewRequest(BaseModel):
    """
    Covers both interview lifecycle cases:

    Case 1 — Start interview (first request):
        { "sessionId": "abc-123", "candidate": { ...candidate object... } }

    Case 2 — Continue interview (subsequent requests):
        { "sessionId": "abc-123", "message": "..." }
    """

    sessionId: str = Field(..., description="Unique session identifier")
    candidate: Optional[Candidate] = Field(
        default=None,
        description="Full candidate object. Required on first request only.",
    )
    message: Optional[str] = Field(
        default=None,
        description="Candidate's latest response. Required on all subsequent requests.",
    )


# ---------------------------------------------------------------------------
# Feedback model (only present in the final response)
# ---------------------------------------------------------------------------

class Feedback(BaseModel):
    summary: str = Field(..., description="2–3 sentence overall assessment")
    strengths: list[str] = Field(..., description="Observed strengths from the interview")
    gaps: list[str] = Field(..., description="Identified knowledge or skill gaps")
    next: list[str] = Field(..., description="Actionable next-step recommendations")


# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------

class InterviewResponse(BaseModel):
    """
    Standard response shape for all turns.

    Required fields (per technical-spec.md):
        reply   — the interviewer's message to the candidate
        done    — False during the interview, True on the final response

    Optional fields (non-breaking extensions for the frontend progress UI):
        feedback          — only present when done is True
        topic             — human-readable title of the current curriculum topic
        day               — curriculum day number of the current topic
        total_questions_asked — every interviewer Q including follow-ups
        topics_completed      — topics fully closed (all follow-ups exhausted)
        days_covered          — count of distinct curriculum days covered so far
    """

    # --- Spec-required fields ---
    reply: str
    done: bool

    # --- Final feedback (spec-required when done=True) ---
    feedback: Optional[Feedback] = None

    # --- Progress display fields (optional, non-breaking) ---
    topic: Optional[str] = Field(default=None, description="Current curriculum topic title")
    day: Optional[int] = Field(default=None, description="Current curriculum day number")
    total_questions_asked: Optional[int] = Field(
        default=None,
        description="Every interviewer question asked, including follow-ups",
    )
    topics_completed: Optional[int] = Field(
        default=None,
        description="Number of topics fully closed",
    )
    days_covered: Optional[int] = Field(
        default=None,
        description="Count of distinct curriculum days covered so far",
    )
