"""
Mission scoring logic.

Takes a single CandidateMission (from the API request) and the curriculum
lookup dict, and produces a ScoredMission with a MissionLabel, numeric
priority, and enriched curriculum fields.

All logic is deterministic — no LLM, no randomness.

Scoring rules (grounded in the actual candidates.json field shapes):

  Mission shape 1: { passed: false, attempts: 1-5 }
      → FAILED — confirmed knowledge gap, highest interview priority.

  Mission shape 2: { skipped: true }  (no passed/attempts fields)
      → SKIPPED — candidate may have zero hands-on experience,
        use conceptual questions.

  Mission shape 3: { passed: true, attempts: 4 or 5 }
      → STRUGGLED — passed eventually but with significant difficulty,
        probe for depth.

  Mission shape 4: { passed: true, attempts: 2 or 3 }
      → PARTIAL — passed with some effort, standard depth question.

  Mission shape 5: { passed: true, attempts: 1 }
      → MASTERED — first-try pass, lighter touch / higher-level question.
"""

from __future__ import annotations

from typing import Any

from planner.models import (
    DifficultyLevel,
    MissionLabel,
    ScoredMission,
    label_priority,
)


# ---------------------------------------------------------------------------
# Module membership lookup
# Built from the module records in curriculum.json.
# Each module has a "days" field that is a 2-element [start, end] range.
# ---------------------------------------------------------------------------

def _build_module_map(modules: list[dict[str, Any]]) -> dict[int, tuple[int, str]]:
    """
    Returns a dict mapping day_number → (module_n, module_title).
    Constructed once from the curriculum modules list.
    """
    result: dict[int, tuple[int, str]] = {}
    for mod in modules:
        start, end = mod["days"][0], mod["days"][1]
        for day in range(start, end + 1):
            result[day] = (mod["n"], mod["title"])
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_mission(
    mission: dict[str, Any],
    curriculum_by_day: dict[int, dict[str, Any]],
    module_map: dict[int, tuple[int, str]],
) -> ScoredMission:
    """
    Score a single candidate mission and enrich it with curriculum data.

    Parameters
    ----------
    mission : dict
        One element from candidate["missions"]. Fields present vary by shape:
        - passed=True/False + attempts=int
        - skipped=True (no passed/attempts)
    curriculum_by_day : dict[int, dict]
        Keyed by day number; value is the full day record from curriculum.json.
    module_map : dict[int, tuple[int, str]]
        Maps day_number → (module_n, module_title). Build with _build_module_map.

    Returns
    -------
    ScoredMission
        Fully enriched scored mission ready for the plan builder.
    """
    day: int = mission["day"]
    title: str = mission["title"]
    skipped: bool = bool(mission.get("skipped", False))
    passed: bool | None = mission.get("passed")
    attempts: int | None = mission.get("attempts")

    # --- Determine label ---
    if skipped:
        label = MissionLabel.SKIPPED
    elif passed is False:
        label = MissionLabel.FAILED
    elif passed is True:
        if attempts is not None and attempts >= 4:
            label = MissionLabel.STRUGGLED
        elif attempts is not None and attempts >= 2:
            label = MissionLabel.PARTIAL
        else:
            label = MissionLabel.MASTERED
    else:
        # Defensive fallback: passed is None and not skipped — treat as partial
        label = MissionLabel.PARTIAL

    priority = label_priority(label)

    # --- Enrich with curriculum data ---
    day_record = curriculum_by_day.get(day, {})
    tools: list[str] = day_record.get("tools", [])
    objectives: list[str] = day_record.get("objectives", [])
    day_type: str = day_record.get("type", "BUILD")

    module_n, module_title = module_map.get(day, (0, "Unknown"))

    return ScoredMission(
        day=day,
        title=title,
        label=label,
        priority=priority,
        attempts=attempts,
        passed=passed,
        day_type=day_type,
        tools=tools,
        objectives=objectives,
        module_n=module_n,
        module_title=module_title,
    )


def score_all_missions(
    candidate: dict[str, Any],
    curriculum_by_day: dict[int, dict[str, Any]],
    modules: list[dict[str, Any]],
) -> list[ScoredMission]:
    """
    Score all missions for a candidate and return them sorted by priority
    (highest priority first, i.e. FAILED before SKIPPED before STRUGGLED…).

    Parameters
    ----------
    candidate : dict
        Full candidate object from the API request or candidates.json.
    curriculum_by_day : dict[int, dict]
        From data.loader.curriculum_by_day.
    modules : list[dict]
        From data.loader.modules (the 8 module records).

    Returns
    -------
    list[ScoredMission]
        Sorted by descending priority. Ties broken by day number (ascending)
        to guarantee a stable, deterministic ordering.
    """
    module_map = _build_module_map(modules)
    missions: list[dict[str, Any]] = candidate.get("missions", [])

    scored = [
        score_mission(m, curriculum_by_day, module_map)
        for m in missions
    ]

    # Sort: highest priority first; for equal priority, lower day number first
    scored.sort(key=lambda s: (-s.priority, s.day))
    return scored


# ---------------------------------------------------------------------------
# Difficulty calibration from candidate-level signals
# ---------------------------------------------------------------------------

def calibrate_difficulty(
    years_experience: int,
    overall_fluency: float,
    job_role: str,
) -> DifficultyLevel:
    """
    Determine the baseline difficulty level for questions based on candidate
    background. Used by the builder to set PlannedTopic.difficulty.

    Rules:
      - Senior / architect / 10+ years → ARCHITECTURAL
      - Mid-level (5-9 years) with high fluency → ARCHITECTURAL
      - Mid-level with lower fluency → APPLIED
      - Junior / entry-level (< 5 years) or non-technical background → depends on fluency
      - Non-technical roles always start at CONCEPTUAL regardless of years

    The LLM prompt builder (Task 6) will use this to calibrate question wording.
    """
    NON_TECHNICAL_KEYWORDS = {
        "business analyst", "marketing", "hr manager", "human resources",
        "ux researcher", "it support", "analyst",
    }
    role_lower = job_role.lower()
    is_non_technical = any(kw in role_lower for kw in NON_TECHNICAL_KEYWORDS)

    if is_non_technical:
        return DifficultyLevel.CONCEPTUAL

    if years_experience >= 10:
        return DifficultyLevel.ARCHITECTURAL

    if years_experience >= 5:
        if overall_fluency >= 0.6:
            return DifficultyLevel.ARCHITECTURAL
        return DifficultyLevel.APPLIED

    # < 5 years experience
    if overall_fluency >= 0.7:
        return DifficultyLevel.APPLIED
    return DifficultyLevel.CONCEPTUAL


def compute_max_followups(
    label: MissionLabel,
    base_difficulty: DifficultyLevel,
) -> int:
    """
    How many follow-up questions can the interviewer ask on this topic.

    Rules:
      - FAILED or SKIPPED: up to 2 follow-ups (need to probe depth of gap)
      - STRUGGLED: up to 2 follow-ups at ARCHITECTURAL difficulty, else 1
      - PARTIAL: 1 follow-up
      - MASTERED: 0 follow-ups (they know it — move on)

    The state machine enforces this cap; the LLM may request fewer.
    """
    if label in (MissionLabel.FAILED, MissionLabel.SKIPPED):
        return 2
    if label == MissionLabel.STRUGGLED:
        return 2 if base_difficulty == DifficultyLevel.ARCHITECTURAL else 1
    if label == MissionLabel.PARTIAL:
        return 1
    # MASTERED
    return 0
