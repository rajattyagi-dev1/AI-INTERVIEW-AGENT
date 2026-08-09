"""
POST /api/interview — real interview engine (Task 4).

Flow:
  First request  (candidate present): init session → ask first question
  Subsequent     (message present):   continue session → ask next question
  Final turn:    (can_end() = True):  generate feedback → return done=True
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from data.loader import curriculum_by_day, modules
from interview.prompt_builder import build_feedback_messages, build_turn_messages
from interview.question_engine import get_current_topic_context, process_llm_response
from interview.session_store import (
    SessionState,
    create_session,
    get_session,
)
from llm.factory import get_llm_provider
from models.schemas import Feedback, InterviewRequest, InterviewResponse
from planner.builder import build_interview_plan

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /api/interview
# ---------------------------------------------------------------------------

@router.post("/api/interview", response_model=InterviewResponse)
async def interview(request: InterviewRequest) -> InterviewResponse:

    # ---- Validate -------------------------------------------------------
    if request.candidate is None and request.message is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Bad request: provide 'candidate' to start a new interview "
                "or 'message' to continue an existing one."
            ),
        )

    # ---- Route to init or continue --------------------------------------
    if request.candidate is not None:
        return await _handle_init(request)
    else:
        return await _handle_continue(request)


# ---------------------------------------------------------------------------
# Init — first request with candidate object
# ---------------------------------------------------------------------------

async def _handle_init(request: InterviewRequest) -> InterviewResponse:
    """Build the interview plan and ask the first question."""
    candidate_dict = request.candidate.model_dump()

    # Build the plan using the Task 2 planner
    plan = build_interview_plan(
        candidate=candidate_dict,
        curriculum_by_day=curriculum_by_day,
        modules=modules,
    )

    # Create session state
    state = create_session(
        session_id=request.sessionId,
        candidate=candidate_dict,
        plan=plan,
    )

    # Ask the first question via LLM
    return await _ask_question(state)


# ---------------------------------------------------------------------------
# Continue — subsequent requests with message
# ---------------------------------------------------------------------------

async def _handle_continue(request: InterviewRequest) -> InterviewResponse:
    """Append the candidate's answer to history and ask the next question."""
    state = get_session(request.sessionId)
    if state is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Session '{request.sessionId}' not found. "
                "Send a 'candidate' object to start a new interview."
            ),
        )

    if state.is_done:
        raise HTTPException(
            status_code=400,
            detail="This interview session has already completed.",
        )

    # Avoid appending duplicate user message if retrying the same turn after error
    if not state.history or state.history[-1].get("content") != request.message:
        state.history.append({"role": "user", "content": request.message})

    # Ask the next question (or generate feedback if done)
    return await _ask_question(state)


# ---------------------------------------------------------------------------
# Core turn: ask a question or finish with feedback
# ---------------------------------------------------------------------------

async def _ask_question(state: SessionState) -> InterviewResponse:
    """
    Call the LLM to get the next interviewer message.
    If completion conditions are met, call the LLM again for feedback.
    """
    llm = get_llm_provider()

    # --- Generate interviewer question ---
    messages = build_turn_messages(state)
    try:
        llm_resp = llm.chat(messages, json_mode=True, temperature=0.7)
        raw = llm_resp.content
    except Exception as e:
        status_code = getattr(e, "status_code", None)
        err_str = str(e).lower()
        is_429 = (
            status_code == 429
            or "429" in err_str
            or "quota" in err_str
            or "rate limit" in err_str
            or "resource_exhausted" in err_str
            or "ratelimiterror" in type(e).__name__.lower()
        )
        if is_429:
            raise HTTPException(
                status_code=429,
                detail="LLM API rate limit or quota exceeded (HTTP 429). Please wait a moment and click Retry.",
            )

        # For non-429 unexpected failures, use a canned recovery turn message
        raw = json.dumps({
            "reply": "I'm having a brief technical issue. Could you please repeat your last answer?",
            "wants_followup": True,
            "followup_reason": "technical retry",
        })

    # --- Process the response and update state ---
    result = process_llm_response(raw, state)

    # Append the interviewer's question to history
    state.history.append({"role": "assistant", "content": result.reply})

    topic_title, topic_day = get_current_topic_context(state)

    # --- If interview is not done, return the question ---
    if not result.is_done:
        return InterviewResponse(
            reply=result.reply,
            done=False,
            topic=result.topic_title or topic_title,
            day=result.topic_day or topic_day,
            total_questions_asked=state.total_questions_asked,
            topics_completed=state.topics_completed,
            days_covered=len(state.days_covered),
        )

    # --- Interview complete — generate feedback ---
    feedback = await _generate_feedback(state, llm)

    return InterviewResponse(
        reply="Thank you for completing the interview. Here is your feedback.",
        done=True,
        feedback=feedback,
        topic=None,
        day=None,
        total_questions_asked=state.total_questions_asked,
        topics_completed=state.topics_completed,
        days_covered=len(state.days_covered),
    )


# ---------------------------------------------------------------------------
# Feedback generation
# ---------------------------------------------------------------------------

async def _generate_feedback(state: SessionState, llm) -> Feedback:
    """Call the LLM with a separate feedback prompt and parse the result."""
    messages = build_feedback_messages(state)
    try:
        resp = llm.chat(messages, json_mode=True, temperature=0.3)
        data = json.loads(resp.content)
        if not isinstance(data, dict):
            return _fallback_feedback(state)

        def _to_list(val: Any) -> list[str]:
            if isinstance(val, list):
                return [str(x) for x in val if x is not None and str(x).strip()]
            return []

        strengths = _to_list(data.get("strengths"))
        gaps = _to_list(data.get("gaps"))
        next_steps = _to_list(data.get("next"))

        fallback = _fallback_feedback(state)
        return Feedback(
            summary=str(data.get("summary") or fallback.summary),
            strengths=strengths or fallback.strengths,
            gaps=gaps or fallback.gaps,
            next=next_steps or fallback.next,
        )
    except Exception:
        return _fallback_feedback(state)


def _fallback_feedback(state: SessionState) -> Feedback:
    """Deterministic fallback feedback built from plan data — no LLM call."""
    profile = state.plan.candidate_profile
    from planner.models import MissionLabel

    strengths, gaps, nexts = [], [], []
    for ts in state.topic_states:
        t = ts.topic
        if t.label == MissionLabel.MASTERED:
            strengths.append(f"Strong understanding of {t.title}")
        elif t.label in (MissionLabel.FAILED, MissionLabel.SKIPPED):
            gaps.append(f"Limited exposure to {t.title} (Day {t.day})")
            nexts.append(f"Review {t.title} — revisit the objectives and tools")
        elif t.label == MissionLabel.STRUGGLED:
            nexts.append(f"Deepen understanding of {t.title} through practice")

    if not strengths:
        strengths = ["Completed the AI curriculum"]
    if not gaps:
        gaps = ["No critical gaps identified in covered topics"]

    return Feedback(
        summary=(
            f"{profile.name} completed a {state.total_questions_asked}-question "
            f"technical interview covering {len(state.days_covered)} curriculum days."
        ),
        strengths=strengths[:4],
        gaps=gaps[:4],
        next=nexts[:4] or ["Continue building on completed curriculum topics"],
    )
