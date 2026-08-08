"""
In-memory session store for interview state.

Each interview session is keyed by sessionId. State is held in a plain
Python dataclass — no database, no Redis.

The state machine that drives the interview lives in the router; this
module is purely responsible for storing and retrieving state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from planner.models import InterviewPlan, PlannedTopic


@dataclass
class TopicState:
    """Tracks progress on a single planned topic during the interview."""
    topic: PlannedTopic
    followups_asked: int = 0          # how many follow-ups have been asked on this topic
    is_complete: bool = False         # True once all follow-ups are exhausted or LLM moves on


@dataclass
class SessionState:
    """Full state for one interview session."""
    session_id: str
    candidate: dict                   # raw candidate dict (from request)
    plan: InterviewPlan               # built once at session init

    # Conversation history sent to the LLM on every turn
    history: list[dict] = field(default_factory=list)

    # Plan navigation
    topic_index: int = 0              # which PlannedTopic we are currently on
    topic_states: list[TopicState] = field(default_factory=list)

    # Counters tracked separately (per requirements)
    total_questions_asked: int = 0    # every interviewer Q including follow-ups
    topics_completed: int = 0         # topics fully closed
    days_covered: set[int] = field(default_factory=set)

    # Phase
    is_done: bool = False

    @property
    def current_topic_state(self) -> Optional[TopicState]:
        if self.topic_index < len(self.topic_states):
            return self.topic_states[self.topic_index]
        return None

    @property
    def current_topic(self) -> Optional[PlannedTopic]:
        ts = self.current_topic_state
        return ts.topic if ts else None

    def can_end(self) -> bool:
        """
        The interview MUST NOT end until all three conditions are met.
        This is checked by the router after every turn.
        """
        from planner.models import MIN_QUESTIONS, MIN_DISTINCT_DAYS
        return (
            self.total_questions_asked >= MIN_QUESTIONS
            and len(self.days_covered) >= MIN_DISTINCT_DAYS
            and (self.current_topic_state is None or self.current_topic_state.is_complete)
        )


# ---------------------------------------------------------------------------
# Module-level store — plain dict, one entry per active sessionId
# ---------------------------------------------------------------------------
_store: dict[str, SessionState] = {}


def create_session(session_id: str, candidate: dict, plan: InterviewPlan) -> SessionState:
    """Create and store a new session, replacing any existing one with the same id."""
    topic_states = [TopicState(topic=t) for t in plan.topics]
    state = SessionState(
        session_id=session_id,
        candidate=candidate,
        plan=plan,
        topic_states=topic_states,
    )
    _store[session_id] = state
    return state


def get_session(session_id: str) -> Optional[SessionState]:
    """Return the session state or None if not found."""
    return _store.get(session_id)


def delete_session(session_id: str) -> None:
    """Remove a session (called after feedback is sent or for cleanup)."""
    _store.pop(session_id, None)


def clear_all() -> None:
    """Remove all sessions. Used in tests only."""
    _store.clear()
