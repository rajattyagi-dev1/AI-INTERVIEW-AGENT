"""
Planner package — public re-exports.

Other modules should import from here rather than from submodules directly.

Usage:
    from planner import build_interview_plan, InterviewPlan, PlannedTopic
    from planner import MIN_QUESTIONS, MIN_DISTINCT_DAYS
"""

from planner.builder import build_interview_plan
from planner.models import (
    CandidateProfile,
    DifficultyLevel,
    InterviewPlan,
    MissionLabel,
    MIN_DISTINCT_DAYS,
    MIN_QUESTIONS,
    MIN_TOPICS,
    MAX_TOPICS,
    MAX_TOTAL_TURNS,
    PlannedTopic,
    ScoredMission,
)
from planner.scoring import (
    calibrate_difficulty,
    compute_max_followups,
    score_all_missions,
    score_mission,
)

__all__ = [
    # Builder
    "build_interview_plan",
    # Models
    "CandidateProfile",
    "DifficultyLevel",
    "InterviewPlan",
    "MissionLabel",
    "PlannedTopic",
    "ScoredMission",
    # Constants
    "MIN_QUESTIONS",
    "MIN_DISTINCT_DAYS",
    "MIN_TOPICS",
    "MAX_TOPICS",
    "MAX_TOTAL_TURNS",
    # Scoring helpers
    "calibrate_difficulty",
    "compute_max_followups",
    "score_all_missions",
    "score_mission",
]
