"""
Planner-internal models for the interview planning layer.

These are distinct from the API schemas in models/schemas.py.
They represent the planner's intermediate and output data structures —
the result of running the deterministic plan builder against a candidate
profile and the curriculum.

Nothing in this module communicates with an LLM or generates conversation.
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Mission classification
# ---------------------------------------------------------------------------

class MissionLabel(str, Enum):
    """
    Classification assigned to each candidate mission by the scorer.

    Ordering maps directly to interview priority (higher → probe first):
      FAILED   > SKIPPED > STRUGGLED > PARTIAL > MASTERED
    """
    FAILED   = "failed"    # passed=False — confirmed gap, probe directly
    SKIPPED  = "skipped"   # skipped=True — candidate may have no hands-on exp
    STRUGGLED = "struggled" # passed=True, attempts >= 4
    PARTIAL  = "partial"   # passed=True, attempts 2-3
    MASTERED = "mastered"  # passed=True, attempts == 1


# Numeric priority for sorting (higher number = interview first)
_LABEL_PRIORITY: dict[MissionLabel, int] = {
    MissionLabel.FAILED:    50,
    MissionLabel.SKIPPED:   40,
    MissionLabel.STRUGGLED: 30,
    MissionLabel.PARTIAL:   20,
    MissionLabel.MASTERED:  10,
}

def label_priority(label: MissionLabel) -> int:
    return _LABEL_PRIORITY[label]


# ---------------------------------------------------------------------------
# Difficulty level for question generation (used by LLM in Task 3+)
# ---------------------------------------------------------------------------

class DifficultyLevel(str, Enum):
    CONCEPTUAL    = "conceptual"    # definitions, intuitions, no code
    APPLIED       = "applied"       # usage, tradeoffs, moderate depth
    ARCHITECTURAL = "architectural" # system design, integration, deep tradeoffs


# ---------------------------------------------------------------------------
# Scored mission — one entry per candidate mission after scoring
# ---------------------------------------------------------------------------

@dataclass
class ScoredMission:
    """
    The output of scoring a single candidate mission.
    Enriched with the full curriculum day record.
    """
    day: int
    title: str
    label: MissionLabel
    priority: int                       # numeric sort key
    attempts: Optional[int]             # None for skipped missions
    passed: Optional[bool]              # None for skipped missions

    # From curriculum_by_day[day]
    day_type: str                       # SETUP | BUILD | LEARN | SHIP_IT | OPTIMIZE | CAPSTONE
    tools: list[str]                    # curriculum tools for this day
    objectives: list[str]               # curriculum objectives (always 5)
    module_n: int                       # 1-8
    module_title: str                   # e.g. "Embeddings & Vector Search"


# ---------------------------------------------------------------------------
# Planned topic — one slot in the final interview question plan
# ---------------------------------------------------------------------------

@dataclass
class PlannedTopic:
    """
    A single interview topic in the ordered question plan.

    Each PlannedTopic corresponds to one curriculum day and will produce
    one primary question plus up to `max_followups` follow-up questions.

    total_questions contribution = 1 (primary) + up to max_followups
    """
    day: int
    title: str
    label: MissionLabel
    module_n: int
    module_title: str
    day_type: str
    tools: list[str]
    objectives: list[str]
    difficulty: DifficultyLevel
    max_followups: int                  # 0, 1, or 2 — set by scoring + candidate signals
    assessment_notes: str               # human-readable rationale for LLM prompt builder


# ---------------------------------------------------------------------------
# Candidate difficulty profile — aggregate of candidate-level signals
# ---------------------------------------------------------------------------

@dataclass
class CandidateProfile:
    """
    Summarises the candidate's background for difficulty calibration.
    Derived purely from the candidate object; no LLM involved.
    """
    name: str
    job_role: str
    years_experience: int
    education: str

    # Derived from signals
    overall_fluency: float              # missionsFirstTry / missionsCompleted, range 0.0–1.0
    commit_days: int
    missions_completed: int
    missions_first_try: int

    # Derived from missions
    total_missions: int
    failed_count: int
    skipped_count: int
    struggled_count: int                # passed with attempts >= 4

    # Calibrated difficulty for the majority of questions
    base_difficulty: DifficultyLevel


# ---------------------------------------------------------------------------
# Interview plan — the final output of the plan builder
# ---------------------------------------------------------------------------

@dataclass
class InterviewPlan:
    """
    The complete, ordered interview plan for one candidate session.

    Guarantees (enforced by builder):
      - len(topics) >= MIN_TOPICS (6 topics produces ≥ 8 questions
        when follow-ups are counted)
      - len({t.day for t in topics}) >= MIN_DISTINCT_DAYS (4)
      - topics are ordered by priority (gaps/failures first)

    The interview state machine (Task 5+) will walk through topics in order,
    tracking total_questions_asked, topics_completed, and days_covered.
    """
    candidate_profile: CandidateProfile
    topics: list[PlannedTopic]          # ordered: highest priority first

    # Convenience aggregates (computed by builder)
    distinct_days: int                  # len({t.day for t in topics})
    distinct_modules: int               # len({t.module_n for t in topics})
    estimated_min_questions: int        # sum of 1 + max_followups for each topic

    # Planning metadata
    has_failed_missions: bool
    has_skipped_missions: bool
    planning_notes: list[str]           # audit trail of builder decisions


# ---------------------------------------------------------------------------
# Minimum plan constraints — single source of truth
# Used by both the builder (to guarantee the plan) and the
# state machine (to decide when the interview can end).
# ---------------------------------------------------------------------------

MIN_QUESTIONS: int = 8          # total_questions_asked must reach this
MIN_DISTINCT_DAYS: int = 4      # days_covered must reach this
MIN_TOPICS: int = 6             # topics in the plan (ensures ≥8 Qs with follow-ups)
MAX_TOPICS: int = 10            # cap to prevent runaway interviews
MAX_TOTAL_TURNS: int = 20       # absolute ceiling across all turns
