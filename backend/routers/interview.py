"""
POST /api/interview — stub implementation (Task 1 scaffolding).

This router validates the request shape and returns a hardcoded stub
response so the endpoint contract can be verified before any interview
logic is wired in.

Behaviour:
  - First request (candidate present, no message):
      Returns a welcome stub with done=False.
  - Subsequent requests (message present, no candidate):
      Echoes the message back with done=False.
  - Neither candidate nor message:
      Returns HTTP 400.
  - Both candidate and message:
      Treated as a first request (candidate takes precedence).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from models.schemas import Feedback, InterviewRequest, InterviewResponse

router = APIRouter()


@router.post("/api/interview", response_model=InterviewResponse)
async def interview(request: InterviewRequest) -> InterviewResponse:
    """
    Stub endpoint — validates request shape and returns a canned response.
    Full interview logic will be added in subsequent tasks.
    """

    # --- Validate: must supply either candidate (init) or message (continue) ---
    if request.candidate is None and request.message is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Bad request: provide 'candidate' to start a new interview "
                "or 'message' to continue an existing one."
            ),
        )

    # --- Case 1: First request — initialise session ---
    if request.candidate is not None:
        candidate_name = request.candidate.member.name
        return InterviewResponse(
            reply=(
                f"Welcome, {candidate_name}. "
                "I'm your AI technical interviewer. "
                "Let's begin — this is a stub response and will be replaced "
                "with real interview logic in the next task."
            ),
            done=False,
            topic="[stub] Waiting for interview engine",
            day=None,
            total_questions_asked=0,
            topics_completed=0,
            days_covered=0,
        )

    # --- Case 2: Continuation turn ---
    return InterviewResponse(
        reply=(
            f"[Stub] You said: \"{request.message}\". "
            "The interview engine is not yet implemented."
        ),
        done=False,
        topic="[stub] Waiting for interview engine",
        day=None,
        total_questions_asked=0,
        topics_completed=0,
        days_covered=0,
    )
