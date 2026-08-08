"""
Question engine — deterministic state transitions for the interview.

This module drives the interview state machine:
  - Decides whether to ask a follow-up or advance to the next topic.
  - Records all counters (total_questions_asked, topics_completed, days_covered).
  - Never calls the LLM — that is the router's job.

The LLM response is parsed by process_llm_response() to extract the
reply text and the wants_followup signal. The engine then updates state
and tells the router what to do next.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from interview.session_store import SessionState, TopicState
from planner.models import MAX_TOTAL_TURNS


@dataclass
class TurnResult:
    """What the router should return to the caller after a turn."""
    reply: str             # interviewer message text to return
    is_done: bool          # True → send done:true + feedback
    topic_title: str = ""
    topic_day: Optional[int] = None


def record_question_asked(state: SessionState) -> None:
    """
    Increment total_questions_asked and record days_covered.
    Called once per LLM question output before returning to the caller.
    """
    state.total_questions_asked += 1
    ts = state.current_topic_state
    if ts:
        state.days_covered.add(ts.topic.day)


def process_llm_response(
    raw_content: str,
    state: SessionState,
) -> TurnResult:
    """
    Parse the LLM's JSON response, update session state, and return
    a TurnResult describing what to send back to the frontend.

    The LLM is expected to return:
        {"reply": "...", "wants_followup": bool, "followup_reason": "..."}

    If parsing fails, the raw text is used as the reply and we default
    to not following up (advance to next topic).
    """
    # --- Parse LLM output ---
    reply, wants_followup = _parse_llm_json(raw_content)

    # --- Record this question ---
    record_question_asked(state)

    # --- Decide: follow up or advance ---
    ts = state.current_topic_state
    if ts is None:
        # No more topics — should not normally happen mid-interview
        state.is_done = True
        return TurnResult(reply=reply, is_done=True)

    can_followup = (
        wants_followup
        and ts.followups_asked < ts.topic.max_followups
        and not ts.is_complete
    )

    if can_followup:
        ts.followups_asked += 1
        topic_closed = False
    else:
        _close_current_topic(state)
        topic_closed = True

    # --- Check hard cap ---
    if state.total_questions_asked >= MAX_TOTAL_TURNS:
        _force_close_remaining(state)

    # --- Check completion ---
    from planner.models import MIN_QUESTIONS, MIN_DISTINCT_DAYS

    is_done = (
        state.total_questions_asked >= MIN_QUESTIONS
        and len(state.days_covered) >= MIN_DISTINCT_DAYS
        and topic_closed
    )

    if is_done:
        state.is_done = True

    topic = state.current_topic
    return TurnResult(
        reply=reply,
        is_done=is_done,
        topic_title=topic.title if topic else "",
        topic_day=topic.day if topic else None,
    )


def get_current_topic_context(state: SessionState) -> tuple[str, Optional[int]]:
    """Return (topic_title, topic_day) for the current topic, or ("", None)."""
    topic = state.current_topic
    if topic:
        return topic.title, topic.day
    return "", None


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _parse_llm_json(raw: str) -> tuple[str, bool]:
    """
    Try to parse the LLM's JSON response.
    Returns (reply_text, wants_followup).
    Falls back gracefully if JSON is malformed.
    """
    try:
        data = json.loads(raw.strip())
        reply = str(data.get("reply", raw))
        wants_followup = bool(data.get("wants_followup", False))
        return reply, wants_followup
    except (json.JSONDecodeError, AttributeError, TypeError):
        # LLM returned plain text — use it as the reply, no follow-up
        return raw.strip(), False


def _close_current_topic(state: SessionState) -> None:
    """Mark the current topic complete and advance the topic index."""
    ts = state.current_topic_state
    if ts and not ts.is_complete:
        ts.is_complete = True
        state.topics_completed += 1
        state.days_covered.add(ts.topic.day)
    state.topic_index += 1


def _force_close_remaining(state: SessionState) -> None:
    """Close all remaining topics when the hard cap is reached."""
    while state.topic_index < len(state.topic_states):
        _close_current_topic(state)
