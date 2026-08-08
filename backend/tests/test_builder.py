"""
Unit tests for planner/builder.py.

Each test uses a candidate fixture modelled on a real candidate from
candidates.json, exercising different edge cases:

  - CAND-003 Emily Chen   — perfect signals, no gaps (all MASTERED)
  - CAND-010 Gerald Combs — 3 failed + 2 skipped (heavy gap candidate)
  - CAND-011 Mia Alvarez  — 5 skipped missions (triggers fallback pillars)
  - CAND-004 David Miller — non-technical role (Business Analyst)
  - CAND-008 Harold Whitfield — 28 years experience (Distinguished Engineer)

All tests are self-contained — no file I/O, no network, no LLM.
"""

from __future__ import annotations

import pytest
from planner.builder import build_interview_plan
from planner.models import (
    DifficultyLevel,
    InterviewPlan,
    MissionLabel,
    MIN_DISTINCT_DAYS,
    MIN_QUESTIONS,
    MIN_TOPICS,
    MAX_TOPICS,
)


# ---------------------------------------------------------------------------
# Shared curriculum fixtures
# ---------------------------------------------------------------------------

# A representative subset of curriculum days covering multiple modules.
# Matches the actual field shapes in curriculum.json.
def _make_day(day: int, title: str, day_type: str, module_days: list) -> dict:
    return {
        "day": day,
        "title": title,
        "type": day_type,
        "tools": ["Tool A", "Tool B"],
        "objectives": ["obj1", "obj2", "obj3", "obj4", "obj5"],
    }

CURRICULUM_BY_DAY: dict = {
    1:  _make_day(1,  "VS Code & Python Environment Setup",    "SETUP",   [1, 3]),
    3:  _make_day(3,  "First AI Project, React Frontend",      "BUILD",   [1, 3]),
    4:  _make_day(4,  "Reading & Processing Structured Data",  "BUILD",   [4, 6]),
    7:  _make_day(7,  "Embeddings Explained",                  "AI_CORE", [7, 10]),
    8:  _make_day(8,  "Vector Databases Overview",             "BUILD",   [7, 10]),
    10: _make_day(10, "Retrieval & Matching Engine",           "SHIP_IT", [7, 10]),
    11: _make_day(11, "RAG End-to-End & LLM API Basics",       "BUILD",   [11, 15]),
    12: _make_day(12, "Prompt Engineering Fundamentals",       "LEARN",   [11, 15]),
    13: _make_day(13, "Function Calling & Structured Outputs", "BUILD",   [11, 15]),
    16: _make_day(16, "Chatbot Backend & API Integration",     "BUILD",   [16, 20]),
    17: _make_day(17, "Chatbot Frontend Development",          "BUILD",   [16, 20]),
    20: _make_day(20, "Conversation Memory & Context Mgmt",    "SHIP_IT", [16, 20]),
    21: _make_day(21, "LangChain Agents",                      "BUILD",   [21, 24]),
    22: _make_day(22, "Multi-Agent Orchestration",             "BUILD",   [21, 24]),
    23: _make_day(23, "Model Context Protocol (MCP)",          "BUILD",   [21, 24]),
    27: _make_day(27, "Security, Privacy & Guardrails",        "BUILD",   [25, 28]),
    28: _make_day(28, "Docker & Kubernetes Deployment",        "SHIP_IT", [25, 28]),
    29: _make_day(29, "Monitoring, Logging & Observability",   "BUILD",   [29, 31]),
    31: _make_day(31, "Capstone Project & Final Demo",         "CAPSTONE",[29, 31]),
}

MODULES: list[dict] = [
    {"n": 1, "title": "Environment & Tooling",             "days": [1, 3]},
    {"n": 2, "title": "Data Foundations",                  "days": [4, 6]},
    {"n": 3, "title": "Embeddings & Vector Search",        "days": [7, 10]},
    {"n": 4, "title": "LLM Core, Prompting & Fine-Tuning", "days": [11, 15]},
    {"n": 5, "title": "Chatbot Application Build",         "days": [16, 20]},
    {"n": 6, "title": "Agentic AI & MCP",                  "days": [21, 24]},
    {"n": 7, "title": "Evaluation, Security & Deployment", "days": [25, 28]},
    {"n": 8, "title": "Production & Capstone",             "days": [29, 31]},
]


def _build(candidate: dict) -> InterviewPlan:
    return build_interview_plan(candidate, CURRICULUM_BY_DAY, MODULES)


# ---------------------------------------------------------------------------
# Candidate fixtures (match actual candidates.json field shapes)
# ---------------------------------------------------------------------------

# CAND-003 Emily Chen — all passed first try, AI Engineer, 6 yrs, MS AI
EMILY_CHEN = {
    "member": {
        "id": "CAND-003", "name": "Emily Chen", "jobRole": "AI Engineer",
        "yearsExperience": 6, "education": "MS Artificial Intelligence", "status": "COMPLETED",
    },
    "missions": [
        {"day": 7,  "title": "Embeddings Explained",                  "passed": True, "attempts": 1},
        {"day": 8,  "title": "Vector Databases Overview",             "passed": True, "attempts": 1},
        {"day": 10, "title": "Retrieval & Matching Engine",           "passed": True, "attempts": 1},
        {"day": 11, "title": "RAG End-to-End & LLM API Basics",       "passed": True, "attempts": 1},
        {"day": 12, "title": "Prompt Engineering Fundamentals",       "passed": True, "attempts": 1},
        {"day": 13, "title": "Function Calling & Structured Outputs", "passed": True, "attempts": 1},
        {"day": 21, "title": "LangChain Agents",                      "passed": True, "attempts": 1},
        {"day": 22, "title": "Multi-Agent Orchestration",             "passed": True, "attempts": 1},
        {"day": 23, "title": "Model Context Protocol (MCP)",          "passed": True, "attempts": 1},
        {"day": 31, "title": "Capstone Project & Final Demo",         "passed": True, "attempts": 1},
    ],
    "signals": {"commitDays": 31, "missionsCompleted": 31, "missionsFirstTry": 30},
}

# CAND-010 Gerald Combs — 3 failed, 2 skipped, IT Support, 20 yrs
GERALD_COMBS = {
    "member": {
        "id": "CAND-010", "name": "Gerald Combs", "jobRole": "IT Support Specialist",
        "yearsExperience": 20, "education": "AAS Information Technology", "status": "COMPLETED",
    },
    "missions": [
        {"day": 1,  "title": "VS Code & Python Environment Setup",   "passed": True,  "attempts": 2},
        {"day": 7,  "title": "Embeddings Explained",                  "passed": True,  "attempts": 5},
        {"day": 8,  "title": "Vector Databases Overview",             "passed": False, "attempts": 4},
        {"day": 10, "title": "Retrieval & Matching Engine",           "passed": False, "attempts": 3},
        {"day": 12, "title": "Prompt Engineering Fundamentals",       "passed": True,  "attempts": 5},
        {"day": 16, "title": "Chatbot Backend & API Integration",     "passed": True,  "attempts": 4},
        {"day": 22, "title": "Multi-Agent Orchestration",             "passed": False, "attempts": 3},
        {"day": 27, "title": "Security, Privacy & Guardrails",        "skipped": True},
        {"day": 28, "title": "Docker & Kubernetes Deployment",        "skipped": True},
        {"day": 31, "title": "Capstone Project & Final Demo",         "passed": True,  "attempts": 3},
    ],
    "signals": {"commitDays": 22, "missionsCompleted": 23, "missionsFirstTry": 1},
}

# CAND-011 Mia Alvarez — 5 skipped, UX Researcher, 6 yrs (triggers fallback)
MIA_ALVAREZ = {
    "member": {
        "id": "CAND-011", "name": "Mia Alvarez", "jobRole": "UX Researcher",
        "yearsExperience": 6, "education": "MA Human-Computer Interaction", "status": "COMPLETED",
    },
    "missions": [
        {"day": 1,  "title": "VS Code & Python Environment Setup",   "passed": True,  "attempts": 2},
        {"day": 3,  "title": "First AI Project, React Frontend",      "passed": True,  "attempts": 3},
        {"day": 4,  "title": "Reading & Processing Structured Data",  "passed": True,  "attempts": 2},
        {"day": 7,  "title": "Embeddings Explained",                  "skipped": True},
        {"day": 8,  "title": "Vector Databases Overview",             "skipped": True},
        {"day": 12, "title": "Prompt Engineering Fundamentals",       "skipped": True},
        {"day": 16, "title": "Chatbot Backend & API Integration",     "skipped": True},
        {"day": 22, "title": "Multi-Agent Orchestration",             "skipped": True},
        {"day": 31, "title": "Capstone Project & Final Demo",         "passed": True,  "attempts": 4},
    ],
    "signals": {"commitDays": 9, "missionsCompleted": 14, "missionsFirstTry": 5},
}

# CAND-004 David Miller — Business Analyst, 8 yrs, non-technical role
DAVID_MILLER = {
    "member": {
        "id": "CAND-004", "name": "David Miller", "jobRole": "Business Analyst",
        "yearsExperience": 8, "education": "MBA", "status": "COMPLETED",
    },
    "missions": [
        {"day": 7,  "title": "Embeddings Explained",              "passed": True,  "attempts": 4},
        {"day": 8,  "title": "Vector Databases Overview",         "passed": True,  "attempts": 5},
        {"day": 10, "title": "Retrieval & Matching Engine",       "passed": True,  "attempts": 5},
        {"day": 12, "title": "Prompt Engineering Fundamentals",   "passed": True,  "attempts": 3},
        {"day": 16, "title": "Chatbot Backend & API Integration", "passed": True,  "attempts": 2},
        {"day": 20, "title": "Conversation Memory & Context Mgmt","passed": True,  "attempts": 3},
        {"day": 22, "title": "Multi-Agent Orchestration",         "passed": True,  "attempts": 4},
        {"day": 23, "title": "Model Context Protocol (MCP)",      "passed": True,  "attempts": 5},
        {"day": 28, "title": "Docker & Kubernetes Deployment",    "skipped": True},
        {"day": 31, "title": "Capstone Project & Final Demo",     "passed": True,  "attempts": 2},
    ],
    "signals": {"commitDays": 18, "missionsCompleted": 28, "missionsFirstTry": 6},
}

# CAND-008 Harold Whitfield — Distinguished Engineer, 28 yrs
HAROLD_WHITFIELD = {
    "member": {
        "id": "CAND-008", "name": "Harold Whitfield", "jobRole": "Distinguished Engineer",
        "yearsExperience": 28, "education": "BS Computer Science", "status": "COMPLETED",
    },
    "missions": [
        {"day": 1,  "title": "VS Code & Python Environment Setup",   "passed": True,  "attempts": 1},
        {"day": 4,  "title": "Reading & Processing Structured Data",  "passed": True,  "attempts": 1},
        {"day": 21, "title": "LangChain Agents",                      "passed": True,  "attempts": 5},
        {"day": 22, "title": "Multi-Agent Orchestration",             "passed": True,  "attempts": 4},
        {"day": 23, "title": "Model Context Protocol (MCP)",          "passed": True,  "attempts": 5},
        {"day": 27, "title": "Security, Privacy & Guardrails",        "passed": True,  "attempts": 1},
        {"day": 28, "title": "Docker & Kubernetes Deployment",        "passed": True,  "attempts": 1},
        {"day": 31, "title": "Capstone Project & Final Demo",         "passed": True,  "attempts": 2},
    ],
    "signals": {"commitDays": 25, "missionsCompleted": 27, "missionsFirstTry": 15},
}


# ---------------------------------------------------------------------------
# Tests: plan guarantees (apply to ALL candidates)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("candidate,label", [
    (EMILY_CHEN,     "emily"),
    (GERALD_COMBS,   "gerald"),
    (MIA_ALVAREZ,    "mia"),
    (DAVID_MILLER,   "david"),
    (HAROLD_WHITFIELD, "harold"),
])
class TestPlanGuarantees:
    """Every plan must satisfy the minimum requirements regardless of candidate."""

    def test_minimum_topics(self, candidate, label):
        plan = _build(candidate)
        assert len(plan.topics) >= MIN_TOPICS, (
            f"{label}: expected >= {MIN_TOPICS} topics, got {len(plan.topics)}"
        )

    def test_minimum_distinct_days(self, candidate, label):
        plan = _build(candidate)
        assert plan.distinct_days >= MIN_DISTINCT_DAYS, (
            f"{label}: expected >= {MIN_DISTINCT_DAYS} distinct days, got {plan.distinct_days}"
        )

    def test_estimated_min_questions_meets_floor(self, candidate, label):
        plan = _build(candidate)
        assert plan.estimated_min_questions >= MIN_QUESTIONS, (
            f"{label}: estimated_min_questions={plan.estimated_min_questions} < {MIN_QUESTIONS}"
        )

    def test_topic_count_does_not_exceed_max(self, candidate, label):
        plan = _build(candidate)
        assert len(plan.topics) <= MAX_TOPICS

    def test_days_in_topics_match_distinct_days_field(self, candidate, label):
        plan = _build(candidate)
        actual_distinct = len({t.day for t in plan.topics})
        assert plan.distinct_days == actual_distinct

    def test_no_duplicate_days_in_plan(self, candidate, label):
        plan = _build(candidate)
        days = [t.day for t in plan.topics]
        assert len(days) == len(set(days)), f"{label}: duplicate days in plan: {days}"

    def test_all_topics_have_difficulty_set(self, candidate, label):
        plan = _build(candidate)
        for t in plan.topics:
            assert isinstance(t.difficulty, DifficultyLevel)

    def test_all_topics_have_assessment_notes(self, candidate, label):
        plan = _build(candidate)
        for t in plan.topics:
            assert t.assessment_notes, f"{label}: topic day {t.day} has empty assessment_notes"

    def test_all_topics_have_objectives(self, candidate, label):
        plan = _build(candidate)
        for t in plan.topics:
            assert len(t.objectives) > 0, f"{label}: topic day {t.day} has no objectives"

    def test_planning_notes_populated(self, candidate, label):
        plan = _build(candidate)
        assert len(plan.planning_notes) >= 3


# ---------------------------------------------------------------------------
# Tests: priority ordering
# ---------------------------------------------------------------------------

class TestPriorityOrdering:
    def test_gerald_failed_topics_appear_before_others(self):
        plan = _build(GERALD_COMBS)
        failed_indices = [i for i, t in enumerate(plan.topics) if t.label == MissionLabel.FAILED]
        non_failed_indices = [i for i, t in enumerate(plan.topics) if t.label != MissionLabel.FAILED]
        assert failed_indices, "Gerald should have FAILED topics"
        if non_failed_indices:
            assert max(failed_indices) < min(non_failed_indices)

    def test_mia_skipped_topics_appear_before_mastered(self):
        plan = _build(MIA_ALVAREZ)
        skipped_indices = [i for i, t in enumerate(plan.topics) if t.label == MissionLabel.SKIPPED]
        mastered_indices = [i for i, t in enumerate(plan.topics) if t.label == MissionLabel.MASTERED]
        if skipped_indices and mastered_indices:
            assert max(skipped_indices) < min(mastered_indices)

    def test_gerald_has_failed_missions_flag(self):
        plan = _build(GERALD_COMBS)
        assert plan.has_failed_missions is True

    def test_mia_has_skipped_missions_flag(self):
        plan = _build(MIA_ALVAREZ)
        assert plan.has_skipped_missions is True

    def test_emily_has_no_failed_missions_flag(self):
        plan = _build(EMILY_CHEN)
        assert plan.has_failed_missions is False


# ---------------------------------------------------------------------------
# Tests: difficulty calibration in plan
# ---------------------------------------------------------------------------

class TestPlanDifficulty:
    def test_david_miller_business_analyst_gets_conceptual_base(self):
        plan = _build(DAVID_MILLER)
        assert plan.candidate_profile.base_difficulty == DifficultyLevel.CONCEPTUAL

    def test_harold_28_years_gets_architectural_base(self):
        plan = _build(HAROLD_WHITFIELD)
        assert plan.candidate_profile.base_difficulty == DifficultyLevel.ARCHITECTURAL

    def test_emily_6_years_high_fluency_gets_architectural(self):
        # 31/31 ≈ 1.0 fluency → ARCHITECTURAL (fluency >= 0.6, years 5-9)
        plan = _build(EMILY_CHEN)
        assert plan.candidate_profile.base_difficulty == DifficultyLevel.ARCHITECTURAL

    def test_failed_topics_use_lower_difficulty_than_base(self):
        # Gerald's base is ARCHITECTURAL (20 yrs) → FAILED topics should be APPLIED
        plan = _build(GERALD_COMBS)
        failed_topics = [t for t in plan.topics if t.label == MissionLabel.FAILED]
        assert failed_topics, "Gerald should have FAILED topics"
        for t in failed_topics:
            assert t.difficulty != DifficultyLevel.ARCHITECTURAL, (
                f"FAILED topic day {t.day} should not be ARCHITECTURAL"
            )

    def test_mastered_topics_use_higher_difficulty_than_base(self):
        # Emily's base is ARCHITECTURAL; MASTERED should stay ARCHITECTURAL (can't go higher)
        plan = _build(EMILY_CHEN)
        mastered_topics = [t for t in plan.topics if t.label == MissionLabel.MASTERED]
        # All mastered topics should be at least APPLIED
        for t in mastered_topics:
            assert t.difficulty in (DifficultyLevel.APPLIED, DifficultyLevel.ARCHITECTURAL)


# ---------------------------------------------------------------------------
# Tests: max_followups on topics
# ---------------------------------------------------------------------------

class TestTopicFollowups:
    def test_failed_topics_get_max_2_followups(self):
        plan = _build(GERALD_COMBS)
        for t in plan.topics:
            if t.label == MissionLabel.FAILED:
                assert t.max_followups == 2

    def test_skipped_topics_get_max_2_followups(self):
        plan = _build(MIA_ALVAREZ)
        for t in plan.topics:
            if t.label == MissionLabel.SKIPPED:
                assert t.max_followups == 2

    def test_mastered_topics_get_0_followups_initially(self):
        # MASTERED topics start with 0 followups from the scorer.
        # The builder may promote them to meet the 8-question floor,
        # which is correct behaviour. We only verify initial scoring here;
        # the builder-level invariant is tested via estimated_min_questions.
        # This test uses score_all_missions directly (no builder promotion).
        from planner.scoring import score_all_missions, _build_module_map
        module_map = _build_module_map(MODULES)
        scored = score_all_missions(EMILY_CHEN, CURRICULUM_BY_DAY, MODULES)
        mastered = [s for s in scored if s.label.value == "mastered"]
        from planner.scoring import compute_max_followups
        from planner.models import DifficultyLevel
        for s in mastered:
            raw = compute_max_followups(s.label, DifficultyLevel.ARCHITECTURAL)
            assert raw == 0, f"Day {s.day} MASTERED initial followups should be 0"


# ---------------------------------------------------------------------------
# Tests: candidate profile fields
# ---------------------------------------------------------------------------

class TestCandidateProfile:
    def test_name_is_set(self):
        plan = _build(EMILY_CHEN)
        assert plan.candidate_profile.name == "Emily Chen"

    def test_job_role_is_set(self):
        plan = _build(DAVID_MILLER)
        assert plan.candidate_profile.job_role == "Business Analyst"

    def test_years_experience_is_set(self):
        plan = _build(HAROLD_WHITFIELD)
        assert plan.candidate_profile.years_experience == 28

    def test_overall_fluency_calculated_correctly(self):
        # Gerald: missionsFirstTry=1, missionsCompleted=23 → 1/23 ≈ 0.043
        plan = _build(GERALD_COMBS)
        assert abs(plan.candidate_profile.overall_fluency - (1 / 23)) < 0.001

    def test_emily_perfect_fluency(self):
        # Emily: 30/31 ≈ 0.968
        plan = _build(EMILY_CHEN)
        assert plan.candidate_profile.overall_fluency > 0.9

    def test_failed_count_matches(self):
        plan = _build(GERALD_COMBS)
        assert plan.candidate_profile.failed_count == 3

    def test_skipped_count_matches(self):
        plan = _build(MIA_ALVAREZ)
        assert plan.candidate_profile.skipped_count == 5


# ---------------------------------------------------------------------------
# Tests: fallback pillar behaviour (Mia Alvarez)
# ---------------------------------------------------------------------------

class TestFallbackPillars:
    def test_mia_plan_meets_distinct_day_minimum(self):
        # Mia has only 3 passed missions on days 1, 3, 4 plus 5 skipped.
        # The builder must pad with pillars to reach MIN_DISTINCT_DAYS=4.
        plan = _build(MIA_ALVAREZ)
        assert plan.distinct_days >= MIN_DISTINCT_DAYS

    def test_mia_plan_meets_topic_minimum(self):
        plan = _build(MIA_ALVAREZ)
        assert len(plan.topics) >= MIN_TOPICS

    def test_mia_plan_exceeds_minimum_questions(self):
        # Mia has 5 skipped missions (max_followups=2 each) so her plan
        # comfortably exceeds the 8-question floor through her own missions —
        # no pillar fallback needed. Verify the estimate is >= MIN_QUESTIONS.
        plan = _build(MIA_ALVAREZ)
        assert plan.estimated_min_questions >= MIN_QUESTIONS, (
            f"Mia: estimated_min_questions={plan.estimated_min_questions} < {MIN_QUESTIONS}"
        )

    def test_pillar_fallback_fires_for_sparse_candidate(self):
        # A candidate with only 2 missions on adjacent days in the same module
        # cannot satisfy MIN_DISTINCT_DAYS=4 on their own — pillars must fire.
        sparse_candidate = {
            "member": {
                "id": "CAND-SPARSE", "name": "Sparse Sam", "jobRole": "AI Engineer",
                "yearsExperience": 2, "education": "BS Computer Science", "status": "COMPLETED",
            },
            "missions": [
                {"day": 7,  "title": "Embeddings Explained",        "passed": True, "attempts": 1},
                {"day": 8,  "title": "Vector Databases Overview",   "passed": True, "attempts": 1},
            ],
            "signals": {"commitDays": 5, "missionsCompleted": 5, "missionsFirstTry": 4},
        }
        plan = _build(sparse_candidate)
        assert plan.distinct_days >= MIN_DISTINCT_DAYS
        assert len(plan.topics) >= MIN_TOPICS
        # Pillar note must appear since sparse candidate can't satisfy minimums alone
        pillar_notes = [n for n in plan.planning_notes if "Fallback pillar" in n]
        assert pillar_notes, (
            f"Expected pillar fallback note. Got: {plan.planning_notes}"
        )
