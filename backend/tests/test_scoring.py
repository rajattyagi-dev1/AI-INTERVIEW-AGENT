"""
Unit tests for planner/scoring.py.

All test fixtures use the actual field shapes present in candidates.json:
  - { passed: true,  attempts: int }   — passed missions
  - { passed: false, attempts: int }   — failed missions
  - { skipped: true }                  — skipped missions (no passed/attempts)

Tests are self-contained — no file I/O, no network, no LLM.
"""

from __future__ import annotations

import pytest
from planner.scoring import (
    calibrate_difficulty,
    compute_max_followups,
    score_mission,
    score_all_missions,
    _build_module_map,
)
from planner.models import (
    DifficultyLevel,
    MissionLabel,
)


# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

# Minimal curriculum_by_day used across tests.
# Fields match the actual curriculum.json day record shape.
CURRICULUM_BY_DAY: dict = {
    7: {
        "day": 7,
        "title": "Embeddings Explained",
        "type": "AI_CORE",
        "tools": ["Sentence Transformers", "OpenAI Embeddings", "Scikit-learn", "Matplotlib"],
        "objectives": [
            "Understand how text is converted into vector embeddings",
            "Generate embeddings for every knowledge base chunk",
            "Store embeddings alongside the original documents",
            "Visualize embedding clusters using PCA",
            "Analyze whether similar healthcare concepts cluster together",
        ],
    },
    8: {
        "day": 8,
        "title": "Vector Databases Overview",
        "type": "BUILD",
        "tools": ["ChromaDB", "Pinecone"],
        "objectives": [
            "Learn the role of vector databases in RAG applications",
            "Set up a local Chroma vector database",
            "Create a cloud-based Pinecone index for comparison",
            "Compare local and managed vector database solutions",
            "Select the most suitable database for the chatbot project",
        ],
    },
    12: {
        "day": 12,
        "title": "Prompt Engineering Fundamentals",
        "type": "LEARN",
        "tools": ["LLMs", "Prompt Templates"],
        "objectives": [
            "Understand zero-shot, few-shot, and chain-of-thought prompting",
            "Design multiple system prompt variations for the chatbot",
            "Compare prompts based on accuracy, compliance, and tone",
            "Evaluate prompt performance using a fixed question set",
            "Finalize the production-ready system prompt",
        ],
    },
    22: {
        "day": 22,
        "title": "Multi-Agent Orchestration",
        "type": "BUILD",
        "tools": ["CrewAI", "LangGraph", "Python"],
        "objectives": [
            "Create specialized agents for different healthcare domains",
            "Build a router agent that delegates requests to the correct specialist",
            "Implement a complete multi-agent workflow",
            "Compare multi-agent performance with a single-agent architecture",
            "Identify scenarios where multiple agents provide measurable benefits",
        ],
    },
    28: {
        "day": 28,
        "title": "Docker & Kubernetes Deployment",
        "type": "SHIP_IT",
        "tools": ["Docker", "Kubernetes", "FastAPI", "React"],
        "objectives": [
            "Containerize the chatbot backend and frontend using Docker",
            "Deploy the application to a Kubernetes cluster",
            "Configure health checks and environment variables",
            "Verify the deployed chatbot functions correctly",
            "Prepare the application for production hosting",
        ],
    },
}

# Minimal modules list matching curriculum.json structure.
MODULES: list[dict] = [
    {"n": 1, "title": "Environment & Tooling",            "days": [1, 3]},
    {"n": 2, "title": "Data Foundations",                 "days": [4, 6]},
    {"n": 3, "title": "Embeddings & Vector Search",       "days": [7, 10]},
    {"n": 4, "title": "LLM Core, Prompting & Fine-Tuning","days": [11, 15]},
    {"n": 5, "title": "Chatbot Application Build",        "days": [16, 20]},
    {"n": 6, "title": "Agentic AI & MCP",                 "days": [21, 24]},
    {"n": 7, "title": "Evaluation, Security & Deployment","days": [25, 28]},
    {"n": 8, "title": "Production & Capstone",            "days": [29, 31]},
]


# ---------------------------------------------------------------------------
# Tests: _build_module_map
# ---------------------------------------------------------------------------

class TestBuildModuleMap:
    def test_day_7_is_in_module_3(self):
        m = _build_module_map(MODULES)
        assert m[7] == (3, "Embeddings & Vector Search")

    def test_day_12_is_in_module_4(self):
        m = _build_module_map(MODULES)
        assert m[12] == (4, "LLM Core, Prompting & Fine-Tuning")

    def test_day_28_is_in_module_7(self):
        m = _build_module_map(MODULES)
        assert m[28] == (7, "Evaluation, Security & Deployment")

    def test_day_22_is_in_module_6(self):
        m = _build_module_map(MODULES)
        assert m[22] == (6, "Agentic AI & MCP")

    def test_all_31_days_are_mapped(self):
        # Build with the full module list covering days 1-31
        m = _build_module_map(MODULES)
        # Our minimal MODULES covers days 1-31; verify boundaries
        assert 1 in m   # start of module 1
        assert 3 in m   # end of module 1
        assert 29 in m  # start of module 8
        assert 31 in m  # end of module 8


# ---------------------------------------------------------------------------
# Tests: score_mission — the five label rules
# ---------------------------------------------------------------------------

class TestScoreMission:
    """Tests for each of the 5 mission shapes from candidates.json."""

    MODULE_MAP = _build_module_map(MODULES)

    def _score(self, mission: dict):
        return score_mission(mission, CURRICULUM_BY_DAY, self.MODULE_MAP)

    # --- Shape 1: passed=True, attempts=1 → MASTERED ---
    def test_passed_first_try_is_mastered(self):
        sm = self._score({"day": 7, "title": "Embeddings Explained", "passed": True, "attempts": 1})
        assert sm.label == MissionLabel.MASTERED

    # --- Shape 2: passed=True, attempts=2 → PARTIAL ---
    def test_passed_two_attempts_is_partial(self):
        sm = self._score({"day": 7, "title": "Embeddings Explained", "passed": True, "attempts": 2})
        assert sm.label == MissionLabel.PARTIAL

    # --- passed=True, attempts=3 → PARTIAL ---
    def test_passed_three_attempts_is_partial(self):
        sm = self._score({"day": 7, "title": "Embeddings Explained", "passed": True, "attempts": 3})
        assert sm.label == MissionLabel.PARTIAL

    # --- Shape 3: passed=True, attempts=4 → STRUGGLED ---
    def test_passed_four_attempts_is_struggled(self):
        sm = self._score({"day": 12, "title": "Prompt Engineering Fundamentals", "passed": True, "attempts": 4})
        assert sm.label == MissionLabel.STRUGGLED

    # --- passed=True, attempts=5 → STRUGGLED ---
    def test_passed_five_attempts_is_struggled(self):
        sm = self._score({"day": 12, "title": "Prompt Engineering Fundamentals", "passed": True, "attempts": 5})
        assert sm.label == MissionLabel.STRUGGLED

    # --- Shape 4: passed=False, attempts=N → FAILED ---
    def test_failed_mission_is_failed(self):
        sm = self._score({"day": 8, "title": "Vector Databases Overview", "passed": False, "attempts": 4})
        assert sm.label == MissionLabel.FAILED

    def test_failed_mission_with_3_attempts_is_failed(self):
        sm = self._score({"day": 22, "title": "Multi-Agent Orchestration", "passed": False, "attempts": 3})
        assert sm.label == MissionLabel.FAILED

    # --- Shape 5: skipped=True (no passed/attempts) → SKIPPED ---
    def test_skipped_mission_is_skipped(self):
        sm = self._score({"day": 28, "title": "Docker & Kubernetes Deployment", "skipped": True})
        assert sm.label == MissionLabel.SKIPPED

    def test_skipped_mission_has_no_passed_or_attempts(self):
        sm = self._score({"day": 28, "title": "Docker & Kubernetes Deployment", "skipped": True})
        assert sm.passed is None
        assert sm.attempts is None

    # --- Curriculum enrichment ---
    def test_curriculum_fields_are_populated(self):
        sm = self._score({"day": 7, "title": "Embeddings Explained", "passed": True, "attempts": 1})
        assert sm.day_type == "AI_CORE"
        assert "Sentence Transformers" in sm.tools
        assert len(sm.objectives) == 5
        assert sm.module_n == 3
        assert sm.module_title == "Embeddings & Vector Search"

    def test_priority_failed_gt_skipped(self):
        failed = self._score({"day": 8, "title": "...", "passed": False, "attempts": 3})
        skipped = self._score({"day": 8, "title": "...", "skipped": True})
        assert failed.priority > skipped.priority

    def test_priority_skipped_gt_struggled(self):
        skipped = self._score({"day": 8, "title": "...", "skipped": True})
        struggled = self._score({"day": 8, "title": "...", "passed": True, "attempts": 5})
        assert skipped.priority > struggled.priority

    def test_priority_struggled_gt_partial(self):
        struggled = self._score({"day": 8, "title": "...", "passed": True, "attempts": 4})
        partial = self._score({"day": 8, "title": "...", "passed": True, "attempts": 3})
        assert struggled.priority > partial.priority

    def test_priority_partial_gt_mastered(self):
        partial = self._score({"day": 8, "title": "...", "passed": True, "attempts": 2})
        mastered = self._score({"day": 8, "title": "...", "passed": True, "attempts": 1})
        assert partial.priority > mastered.priority


# ---------------------------------------------------------------------------
# Tests: score_all_missions — ordering and completeness
# ---------------------------------------------------------------------------

class TestScoreAllMissions:
    """
    Uses a representative candidate fixture modelled on CAND-010 Gerald Combs
    who has failed (day 8, 10, 22), skipped (day 27, 28), and passed missions.
    """

    CANDIDATE_GERALD = {
        "member": {
            "id": "CAND-010",
            "name": "Gerald Combs",
            "jobRole": "IT Support Specialist",
            "yearsExperience": 20,
            "education": "AAS Information Technology",
            "status": "COMPLETED",
        },
        "missions": [
            {"day": 1,  "title": "VS Code & Python Environment Setup",   "passed": True,  "attempts": 2},
            {"day": 7,  "title": "Embeddings Explained",                  "passed": True,  "attempts": 5},
            {"day": 8,  "title": "Vector Databases Overview",             "passed": False, "attempts": 4},
            {"day": 12, "title": "Prompt Engineering Fundamentals",       "passed": True,  "attempts": 5},
            {"day": 22, "title": "Multi-Agent Orchestration",             "passed": False, "attempts": 3},
            {"day": 27, "title": "Security, Privacy & Guardrails",        "skipped": True},
            {"day": 28, "title": "Docker & Kubernetes Deployment",        "skipped": True},
        ],
        "signals": {"commitDays": 22, "missionsCompleted": 23, "missionsFirstTry": 1},
    }

    # Extend CURRICULUM_BY_DAY with the extra days Gerald has
    EXTENDED_CURRICULUM = {
        **CURRICULUM_BY_DAY,
        1: {"day": 1, "title": "VS Code & Python Environment Setup", "type": "SETUP",
            "tools": ["VS Code", "Python"], "objectives": ["o1", "o2", "o3", "o4", "o5"]},
        27: {"day": 27, "title": "Security, Privacy & Guardrails", "type": "BUILD",
             "tools": ["FastAPI", "Python"], "objectives": ["o1", "o2", "o3", "o4", "o5"]},
    }

    def _score_all(self):
        return score_all_missions(self.CANDIDATE_GERALD, self.EXTENDED_CURRICULUM, MODULES)

    def test_returns_correct_count(self):
        scored = self._score_all()
        assert len(scored) == 7

    def test_failed_missions_appear_first(self):
        scored = self._score_all()
        # Both failed missions (day 8, day 22) must precede all non-failed
        failed = [s for s in scored if s.label == MissionLabel.FAILED]
        assert len(failed) == 2
        first_non_failed_idx = next(
            i for i, s in enumerate(scored) if s.label != MissionLabel.FAILED
        )
        for f in failed:
            assert scored.index(f) < first_non_failed_idx

    def test_skipped_missions_before_struggled(self):
        scored = self._score_all()
        skipped_indices = [i for i, s in enumerate(scored) if s.label == MissionLabel.SKIPPED]
        struggled_indices = [i for i, s in enumerate(scored) if s.label == MissionLabel.STRUGGLED]
        if skipped_indices and struggled_indices:
            assert max(skipped_indices) < min(struggled_indices)

    def test_tie_broken_by_day_ascending(self):
        # Days 8 and 22 are both FAILED — day 8 should come first
        scored = self._score_all()
        failed = [s for s in scored if s.label == MissionLabel.FAILED]
        assert failed[0].day == 8
        assert failed[1].day == 22

    def test_all_labels_assigned(self):
        scored = self._score_all()
        labels = {s.label for s in scored}
        # Gerald has failed, skipped, struggled, partial missions
        assert MissionLabel.FAILED in labels
        assert MissionLabel.SKIPPED in labels
        assert MissionLabel.STRUGGLED in labels


# ---------------------------------------------------------------------------
# Tests: calibrate_difficulty
# ---------------------------------------------------------------------------

class TestCalibrateDifficulty:
    def test_non_technical_role_always_conceptual(self):
        assert calibrate_difficulty(20, 0.9, "Marketing Manager") == DifficultyLevel.CONCEPTUAL

    def test_business_analyst_always_conceptual(self):
        assert calibrate_difficulty(8, 0.8, "Business Analyst") == DifficultyLevel.CONCEPTUAL

    def test_hr_manager_always_conceptual(self):
        assert calibrate_difficulty(10, 0.9, "HR Manager") == DifficultyLevel.CONCEPTUAL

    def test_10_plus_years_is_architectural(self):
        assert calibrate_difficulty(10, 0.5, "Software Engineer") == DifficultyLevel.ARCHITECTURAL

    def test_28_years_is_architectural(self):
        assert calibrate_difficulty(28, 0.9, "Distinguished Engineer") == DifficultyLevel.ARCHITECTURAL

    def test_5_to_9_years_high_fluency_is_architectural(self):
        # fluency >= 0.6
        assert calibrate_difficulty(6, 0.8, "AI Engineer") == DifficultyLevel.ARCHITECTURAL

    def test_5_to_9_years_low_fluency_is_applied(self):
        # fluency < 0.6
        assert calibrate_difficulty(5, 0.4, "Backend Software Engineer") == DifficultyLevel.APPLIED

    def test_under_5_years_high_fluency_is_applied(self):
        # fluency >= 0.7
        assert calibrate_difficulty(4, 0.9, "AI Engineer") == DifficultyLevel.APPLIED

    def test_under_5_years_low_fluency_is_conceptual(self):
        # fluency < 0.7
        assert calibrate_difficulty(1, 0.3, "AI Engineer") == DifficultyLevel.CONCEPTUAL

    def test_zero_years_is_conceptual(self):
        assert calibrate_difficulty(0, 0.5, "Computer Science Intern") == DifficultyLevel.CONCEPTUAL


# ---------------------------------------------------------------------------
# Tests: compute_max_followups
# ---------------------------------------------------------------------------

class TestComputeMaxFollowups:
    def test_failed_gets_2_followups(self):
        assert compute_max_followups(MissionLabel.FAILED, DifficultyLevel.CONCEPTUAL) == 2

    def test_skipped_gets_2_followups(self):
        assert compute_max_followups(MissionLabel.SKIPPED, DifficultyLevel.APPLIED) == 2

    def test_struggled_architectural_gets_2_followups(self):
        assert compute_max_followups(MissionLabel.STRUGGLED, DifficultyLevel.ARCHITECTURAL) == 2

    def test_struggled_applied_gets_1_followup(self):
        assert compute_max_followups(MissionLabel.STRUGGLED, DifficultyLevel.APPLIED) == 1

    def test_struggled_conceptual_gets_1_followup(self):
        assert compute_max_followups(MissionLabel.STRUGGLED, DifficultyLevel.CONCEPTUAL) == 1

    def test_partial_gets_1_followup(self):
        assert compute_max_followups(MissionLabel.PARTIAL, DifficultyLevel.APPLIED) == 1

    def test_mastered_gets_0_followups(self):
        assert compute_max_followups(MissionLabel.MASTERED, DifficultyLevel.ARCHITECTURAL) == 0

    def test_mastered_at_any_difficulty_gets_0(self):
        for diff in DifficultyLevel:
            assert compute_max_followups(MissionLabel.MASTERED, diff) == 0
