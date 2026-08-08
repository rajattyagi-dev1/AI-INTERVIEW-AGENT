"""
Interview plan builder.

Converts a candidate object + loaded curriculum data into a fully
structured InterviewPlan that the interview engine (Tasks 5+) will
execute turn by turn.

All logic is deterministic. No LLM, no randomness.

The builder guarantees:
  - At least MIN_TOPICS (6) planned topics.
  - At least MIN_DISTINCT_DAYS (4) distinct curriculum days.
  - Topics ordered by priority (gaps/failures first).
  - Every topic has a DifficultyLevel and max_followups set.
  - estimated_min_questions >= MIN_QUESTIONS (8).

Fallback topics (curriculum "pillars") are added when the candidate's
own missions would not satisfy the day/topic minimums — for example,
candidates who skipped many missions (e.g. CAND-011 Mia Alvarez).
"""

from __future__ import annotations

from typing import Any

from planner.models import (
    CandidateProfile,
    DifficultyLevel,
    InterviewPlan,
    MissionLabel,
    MIN_DISTINCT_DAYS,
    MIN_QUESTIONS,
    MIN_TOPICS,
    MAX_TOPICS,
    PlannedTopic,
)
from planner.scoring import (
    calibrate_difficulty,
    compute_max_followups,
    score_all_missions,
)


# ---------------------------------------------------------------------------
# Curriculum "pillar" days used as fallback when the candidate has too few
# missions to fill the plan. These are the most universally relevant topics
# across all roles and experience levels.
# ---------------------------------------------------------------------------
_PILLAR_DAYS = [7, 12, 22, 28, 16, 10, 23, 31]   # 8 pillars; ensures MIN_TOPICS=6 reachable


# ---------------------------------------------------------------------------
# Assessment notes — human-readable rationale written into each PlannedTopic.
# The LLM prompt builder (Task 6) will surface these to calibrate questions.
# ---------------------------------------------------------------------------

def _assessment_note(
    label: MissionLabel,
    attempts: int | None,
    difficulty: DifficultyLevel,
    job_role: str,
) -> str:
    role_hint = f" (role: {job_role})" if job_role else ""

    if label == MissionLabel.FAILED:
        return (
            f"Candidate attempted this topic {attempts} time(s) and did not pass{role_hint}. "
            f"Ask directly to probe for fundamental understanding. "
            f"Difficulty: {difficulty.value}."
        )
    if label == MissionLabel.SKIPPED:
        return (
            f"Candidate skipped this topic{role_hint}. "
            f"They may have no hands-on experience. "
            f"Ask conceptual questions; do not assume implementation knowledge. "
            f"Difficulty: {difficulty.value}."
        )
    if label == MissionLabel.STRUGGLED:
        return (
            f"Candidate passed after {attempts} attempt(s){role_hint}. "
            f"Probe for depth — verify understanding beyond surface recall. "
            f"Difficulty: {difficulty.value}."
        )
    if label == MissionLabel.PARTIAL:
        return (
            f"Candidate passed with {attempts} attempt(s){role_hint}. "
            f"Standard depth question. "
            f"Difficulty: {difficulty.value}."
        )
    # MASTERED
    return (
        f"Candidate passed on first try{role_hint}. "
        f"Ask a higher-level or applied question to confirm depth. "
        f"Difficulty: {difficulty.value}."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_interview_plan(
    candidate: dict[str, Any],
    curriculum_by_day: dict[int, dict[str, Any]],
    modules: list[dict[str, Any]],
) -> InterviewPlan:
    """
    Build a fully structured, prioritised interview plan for the given candidate.

    Parameters
    ----------
    candidate : dict
        Full candidate object from the API request (matches candidates.json schema).
    curriculum_by_day : dict[int, dict]
        From data.loader.curriculum_by_day.
    modules : list[dict]
        From data.loader.modules (the 8 module records).

    Returns
    -------
    InterviewPlan
        Ordered list of PlannedTopics ready for the interview state machine.
    """
    member = candidate["member"]
    signals = candidate["signals"]

    # --- 1. Build candidate profile ---
    missions_completed: int = signals["missionsCompleted"]
    missions_first_try: int = signals["missionsFirstTry"]
    overall_fluency: float = (
        missions_first_try / missions_completed
        if missions_completed > 0
        else 0.0
    )

    years_exp: int = member["yearsExperience"]
    job_role: str = member["jobRole"]
    base_difficulty: DifficultyLevel = calibrate_difficulty(
        years_exp, overall_fluency, job_role
    )

    # --- 2. Score all candidate missions ---
    scored = score_all_missions(candidate, curriculum_by_day, modules)

    failed_count   = sum(1 for s in scored if s.label == MissionLabel.FAILED)
    skipped_count  = sum(1 for s in scored if s.label == MissionLabel.SKIPPED)
    struggled_count = sum(1 for s in scored if s.label == MissionLabel.STRUGGLED)

    profile = CandidateProfile(
        name=member["name"],
        job_role=job_role,
        years_experience=years_exp,
        education=member["education"],
        overall_fluency=overall_fluency,
        commit_days=signals["commitDays"],
        missions_completed=missions_completed,
        missions_first_try=missions_first_try,
        total_missions=len(scored),
        failed_count=failed_count,
        skipped_count=skipped_count,
        struggled_count=struggled_count,
        base_difficulty=base_difficulty,
    )

    planning_notes: list[str] = []
    planning_notes.append(
        f"Candidate: {profile.name} | Role: {job_role} | "
        f"Experience: {years_exp} yrs | Base difficulty: {base_difficulty.value}"
    )
    planning_notes.append(
        f"Signals — commitDays: {profile.commit_days}, "
        f"completed: {missions_completed}, firstTry: {missions_first_try}, "
        f"fluency: {overall_fluency:.2f}"
    )
    planning_notes.append(
        f"Mission labels — failed: {failed_count}, skipped: {skipped_count}, "
        f"struggled: {struggled_count}"
    )

    # --- 3. Build primary topic list from scored missions ---
    # Scored is already sorted: FAILED > SKIPPED > STRUGGLED > PARTIAL > MASTERED
    # Within each label, lower day number comes first (stable sort from scorer).
    topics: list[PlannedTopic] = []
    days_used: set[int] = set()

    # Pass 1: include all failed, skipped, and struggled missions (priority gaps)
    for sm in scored:
        if sm.label in (MissionLabel.FAILED, MissionLabel.SKIPPED, MissionLabel.STRUGGLED):
            if sm.day not in days_used:
                difficulty = _topic_difficulty(sm.label, base_difficulty)
                topics.append(_make_topic(sm, difficulty, job_role))
                days_used.add(sm.day)

    planning_notes.append(
        f"Pass 1 (gaps/struggles): {len(topics)} topics from "
        f"{len(days_used)} distinct days"
    )

    # Pass 2: add PARTIAL missions until we have enough topics and days
    for sm in scored:
        if len(topics) >= MAX_TOPICS:
            break
        if sm.label == MissionLabel.PARTIAL and sm.day not in days_used:
            difficulty = _topic_difficulty(sm.label, base_difficulty)
            topics.append(_make_topic(sm, difficulty, job_role))
            days_used.add(sm.day)

    # Pass 3: add MASTERED missions if we still need more topics or days
    for sm in scored:
        if len(topics) >= MAX_TOPICS:
            break
        if (
            sm.label == MissionLabel.MASTERED
            and sm.day not in days_used
            and (len(topics) < MIN_TOPICS or len(days_used) < MIN_DISTINCT_DAYS)
        ):
            difficulty = _topic_difficulty(sm.label, base_difficulty)
            topics.append(_make_topic(sm, difficulty, job_role))
            days_used.add(sm.day)

    planning_notes.append(
        f"After passes 2-3: {len(topics)} topics from {len(days_used)} distinct days"
    )

    # --- 4. Fallback: ensure minimum distinct days with curriculum pillars ---
    if len(days_used) < MIN_DISTINCT_DAYS or len(topics) < MIN_TOPICS:
        for pillar_day in _PILLAR_DAYS:
            if len(days_used) >= MIN_DISTINCT_DAYS and len(topics) >= MIN_TOPICS:
                break
            if pillar_day in days_used:
                continue
            day_record = curriculum_by_day.get(pillar_day)
            if day_record is None:
                continue
            # Build a synthetic scored-mission-like topic for the pillar
            from planner.models import ScoredMission
            # Determine module for this pillar day
            module_n, module_title = _day_to_module(pillar_day, modules)
            sm_pillar = ScoredMission(
                day=pillar_day,
                title=day_record["title"],
                label=MissionLabel.SKIPPED,   # treat as conceptual gap
                priority=0,
                attempts=None,
                passed=None,
                day_type=day_record.get("type", "BUILD"),
                tools=day_record.get("tools", []),
                objectives=day_record.get("objectives", []),
                module_n=module_n,
                module_title=module_title,
            )
            topics.append(_make_topic(sm_pillar, DifficultyLevel.CONCEPTUAL, job_role))
            days_used.add(pillar_day)
            planning_notes.append(
                f"Fallback pillar added: Day {pillar_day} ({day_record['title']})"
            )

    # --- 5. Re-sort after fallback additions ---
    # Primary sort: label priority descending; secondary: day number ascending
    from planner.models import label_priority
    topics.sort(key=lambda t: (-label_priority(t.label), t.day))

    # --- 6. Enforce MAX_TOPICS cap ---
    if len(topics) > MAX_TOPICS:
        topics = topics[:MAX_TOPICS]
        planning_notes.append(f"Capped to {MAX_TOPICS} topics")

    # --- 7. Guarantee estimated_min_questions >= MIN_QUESTIONS ---
    # For candidates who aced every mission (all MASTERED, 0 followups each),
    # the raw count of 1 question per topic may fall below the 8-question floor.
    # Promote max_followups on the highest-priority topics until the floor is met.
    estimated_min_questions = sum(1 + t.max_followups for t in topics)
    if estimated_min_questions < MIN_QUESTIONS:
        shortfall = MIN_QUESTIONS - estimated_min_questions
        for t in topics:
            if shortfall <= 0:
                break
            # Only promote topics that can accept more followups
            # (cap at 2 regardless of what would be needed)
            promotable = 2 - t.max_followups
            if promotable > 0:
                bump = min(promotable, shortfall)
                t.max_followups += bump
                shortfall -= bump
        estimated_min_questions = sum(1 + t.max_followups for t in topics)
        planning_notes.append(
            f"Promoted follow-up counts to guarantee >= {MIN_QUESTIONS} questions. "
            f"Adjusted estimated_min_questions: {estimated_min_questions}"
        )

    # Final aggregate recompute
    distinct_days = len({t.day for t in topics})
    distinct_modules = len({t.module_n for t in topics})
    estimated_min_questions = sum(1 + t.max_followups for t in topics)

    planning_notes.append(
        f"Final plan: {len(topics)} topics | {distinct_days} distinct days | "
        f"{distinct_modules} distinct modules | "
        f"~{estimated_min_questions} min questions "
        f"(floor: {MIN_QUESTIONS})"
    )

    return InterviewPlan(
        candidate_profile=profile,
        topics=topics,
        distinct_days=distinct_days,
        distinct_modules=distinct_modules,
        estimated_min_questions=estimated_min_questions,
        has_failed_missions=failed_count > 0,
        has_skipped_missions=skipped_count > 0,
        planning_notes=planning_notes,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _topic_difficulty(
    label: MissionLabel,
    base_difficulty: DifficultyLevel,
) -> DifficultyLevel:
    """
    Adjust difficulty per topic based on label.

    FAILED / SKIPPED topics always drop one level (probe foundation first).
    MASTERED topics always stay at base (they know it; go deeper).
    Others use base difficulty.
    """
    order = [
        DifficultyLevel.CONCEPTUAL,
        DifficultyLevel.APPLIED,
        DifficultyLevel.ARCHITECTURAL,
    ]
    idx = order.index(base_difficulty)

    if label in (MissionLabel.FAILED, MissionLabel.SKIPPED):
        # Drop one level — candidate may have a gap, start foundational
        return order[max(0, idx - 1)]
    if label == MissionLabel.MASTERED:
        # Bump one level — they know it, challenge them
        return order[min(len(order) - 1, idx + 1)]
    return base_difficulty


def _make_topic(
    sm: "ScoredMission",
    difficulty: DifficultyLevel,
    job_role: str,
) -> PlannedTopic:
    """Construct a PlannedTopic from a ScoredMission."""
    max_followups = compute_max_followups(sm.label, difficulty)
    note = _assessment_note(sm.label, sm.attempts, difficulty, job_role)
    return PlannedTopic(
        day=sm.day,
        title=sm.title,
        label=sm.label,
        module_n=sm.module_n,
        module_title=sm.module_title,
        day_type=sm.day_type,
        tools=sm.tools,
        objectives=sm.objectives,
        difficulty=difficulty,
        max_followups=max_followups,
        assessment_notes=note,
    )


def _day_to_module(
    day: int,
    modules: list[dict[str, Any]],
) -> tuple[int, str]:
    """Return (module_n, module_title) for a given day number."""
    for mod in modules:
        start, end = mod["days"][0], mod["days"][1]
        if start <= day <= end:
            return mod["n"], mod["title"]
    return 0, "Unknown"
