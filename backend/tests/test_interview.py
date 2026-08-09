"""
Focused tests for the Task 4 interview engine:
  - Session store lifecycle
  - Question engine state transitions and counter tracking
  - Prompt builder output shape
  - Completion rules enforcement
  - POST /api/interview via FastAPI TestClient (mock LLM)
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

# Minimal curriculum fixtures mirroring real data shapes
CURRICULUM_BY_DAY = {
    7:  {"day": 7,  "title": "Embeddings Explained",           "type": "AI_CORE", "tools": ["Sentence Transformers"], "objectives": ["o1","o2","o3","o4","o5"]},
    12: {"day": 12, "title": "Prompt Engineering",             "type": "LEARN",   "tools": ["LLMs"],                  "objectives": ["o1","o2","o3","o4","o5"]},
    22: {"day": 22, "title": "Multi-Agent Orchestration",      "type": "BUILD",   "tools": ["CrewAI","LangGraph"],     "objectives": ["o1","o2","o3","o4","o5"]},
    28: {"day": 28, "title": "Docker & Kubernetes Deployment", "type": "SHIP_IT", "tools": ["Docker","Kubernetes"],    "objectives": ["o1","o2","o3","o4","o5"]},
    16: {"day": 16, "title": "Chatbot Backend & API",          "type": "BUILD",   "tools": ["FastAPI"],               "objectives": ["o1","o2","o3","o4","o5"]},
    10: {"day": 10, "title": "Retrieval & Matching Engine",    "type": "SHIP_IT", "tools": ["SQLite","ChromaDB"],      "objectives": ["o1","o2","o3","o4","o5"]},
    23: {"day": 23, "title": "Model Context Protocol",         "type": "BUILD",   "tools": ["MCP Python SDK"],         "objectives": ["o1","o2","o3","o4","o5"]},
    31: {"day": 31, "title": "Capstone Project",               "type": "CAPSTONE","tools": ["FastAPI","React"],        "objectives": ["o1","o2","o3","o4","o5"]},
}
MODULES = [
    {"n": 1, "title": "Environment & Tooling",             "days": [1, 3]},
    {"n": 2, "title": "Data Foundations",                  "days": [4, 6]},
    {"n": 3, "title": "Embeddings & Vector Search",        "days": [7, 10]},
    {"n": 4, "title": "LLM Core, Prompting & Fine-Tuning", "days": [11, 15]},
    {"n": 5, "title": "Chatbot Application Build",         "days": [16, 20]},
    {"n": 6, "title": "Agentic AI & MCP",                  "days": [21, 24]},
    {"n": 7, "title": "Evaluation, Security & Deployment", "days": [25, 28]},
    {"n": 8, "title": "Production & Capstone",             "days": [29, 31]},
]

# A realistic candidate with gaps (triggers FAILED and SKIPPED topics)
CANDIDATE_GERALD = {
    "member": {"id":"CAND-010","name":"Gerald Combs","jobRole":"IT Support Specialist",
               "yearsExperience":20,"education":"AAS Information Technology","status":"COMPLETED"},
    "missions": [
        {"day":7,  "title":"Embeddings Explained",           "passed":True,  "attempts":5},
        {"day":8,  "title":"Vector Databases Overview",      "passed":False, "attempts":4},
        {"day":10, "title":"Retrieval & Matching Engine",    "passed":False, "attempts":3},
        {"day":12, "title":"Prompt Engineering",             "passed":True,  "attempts":5},
        {"day":16, "title":"Chatbot Backend & API",          "passed":True,  "attempts":4},
        {"day":22, "title":"Multi-Agent Orchestration",      "passed":False, "attempts":3},
        {"day":27, "title":"Security, Privacy & Guardrails", "skipped":True},
        {"day":28, "title":"Docker & Kubernetes Deployment", "skipped":True},
        {"day":31, "title":"Capstone Project",               "passed":True,  "attempts":3},
    ],
    "signals":{"commitDays":22,"missionsCompleted":23,"missionsFirstTry":1},
}

def _build_plan(candidate=None):
    from planner.builder import build_interview_plan
    return build_interview_plan(candidate or CANDIDATE_GERALD, CURRICULUM_BY_DAY, MODULES)


# ---------------------------------------------------------------------------
# Session Store Tests
# ---------------------------------------------------------------------------

class TestSessionStore:
    def setup_method(self):
        from interview.session_store import clear_all
        clear_all()

    def test_create_and_get(self):
        from interview.session_store import create_session, get_session
        plan = _build_plan()
        state = create_session("s1", CANDIDATE_GERALD, plan)
        assert get_session("s1") is state

    def test_get_missing_returns_none(self):
        from interview.session_store import get_session
        assert get_session("nonexistent") is None

    def test_create_replaces_existing(self):
        from interview.session_store import create_session, get_session
        plan = _build_plan()
        s1 = create_session("s1", CANDIDATE_GERALD, plan)
        s2 = create_session("s1", CANDIDATE_GERALD, plan)
        assert get_session("s1") is s2
        assert get_session("s1") is not s1

    def test_initial_counters_are_zero(self):
        from interview.session_store import create_session
        plan = _build_plan()
        state = create_session("s1", CANDIDATE_GERALD, plan)
        assert state.total_questions_asked == 0
        assert state.topics_completed == 0
        assert len(state.days_covered) == 0

    def test_topic_states_match_plan(self):
        from interview.session_store import create_session
        plan = _build_plan()
        state = create_session("s1", CANDIDATE_GERALD, plan)
        assert len(state.topic_states) == len(plan.topics)

    def test_current_topic_is_first_planned_topic(self):
        from interview.session_store import create_session
        plan = _build_plan()
        state = create_session("s1", CANDIDATE_GERALD, plan)
        assert state.current_topic is plan.topics[0]

    def test_delete_session(self):
        from interview.session_store import create_session, get_session, delete_session
        plan = _build_plan()
        create_session("s1", CANDIDATE_GERALD, plan)
        delete_session("s1")
        assert get_session("s1") is None

    def test_can_end_false_when_zero_questions(self):
        from interview.session_store import create_session
        plan = _build_plan()
        state = create_session("s1", CANDIDATE_GERALD, plan)
        assert state.can_end() is False

    def test_can_end_requires_min_questions(self):
        from interview.session_store import create_session
        from planner.models import MIN_QUESTIONS, MIN_DISTINCT_DAYS
        plan = _build_plan()
        state = create_session("s1", CANDIDATE_GERALD, plan)
        # Fill days_covered and close current topic but keep questions below floor
        for d in list(CURRICULUM_BY_DAY.keys())[:MIN_DISTINCT_DAYS]:
            state.days_covered.add(d)
        ts = state.current_topic_state
        if ts:
            ts.is_complete = True
        state.total_questions_asked = MIN_QUESTIONS - 1
        assert state.can_end() is False

    def test_can_end_true_when_all_conditions_met(self):
        from interview.session_store import create_session
        from planner.models import MIN_QUESTIONS, MIN_DISTINCT_DAYS
        plan = _build_plan()
        state = create_session("s1", CANDIDATE_GERALD, plan)
        state.total_questions_asked = MIN_QUESTIONS
        for d in list(CURRICULUM_BY_DAY.keys())[:MIN_DISTINCT_DAYS]:
            state.days_covered.add(d)
        # Close the current topic
        ts = state.current_topic_state
        if ts:
            ts.is_complete = True
        state.topic_index = len(state.topic_states)  # past all topics
        assert state.can_end() is True


# ---------------------------------------------------------------------------
# Question Engine Tests
# ---------------------------------------------------------------------------

class TestQuestionEngine:
    def setup_method(self):
        from interview.session_store import clear_all
        clear_all()

    def _make_state(self):
        from interview.session_store import create_session
        plan = _build_plan()
        return create_session("s1", CANDIDATE_GERALD, plan)

    def test_parse_valid_json_response(self):
        from interview.question_engine import _parse_llm_json
        raw = '{"reply": "What is an embedding?", "wants_followup": false, "followup_reason": ""}'
        reply, followup = _parse_llm_json(raw)
        assert reply == "What is an embedding?"
        assert followup is False

    def test_parse_followup_true(self):
        from interview.question_engine import _parse_llm_json
        raw = '{"reply": "Can you elaborate?", "wants_followup": true, "followup_reason": "vague"}'
        reply, followup = _parse_llm_json(raw)
        assert followup is True

    def test_parse_fallback_on_plain_text(self):
        from interview.question_engine import _parse_llm_json
        reply, followup = _parse_llm_json("This is a plain text response")
        assert reply == "This is a plain text response"
        assert followup is False

    def test_parse_fallback_on_invalid_json(self):
        from interview.question_engine import _parse_llm_json
        reply, followup = _parse_llm_json("{not valid json}")
        assert isinstance(reply, str)
        assert followup is False

    def test_record_question_increments_counter(self):
        from interview.question_engine import record_question_asked
        state = self._make_state()
        assert state.total_questions_asked == 0
        record_question_asked(state)
        assert state.total_questions_asked == 1

    def test_record_question_adds_day_to_covered(self):
        from interview.question_engine import record_question_asked
        state = self._make_state()
        first_day = state.current_topic.day
        record_question_asked(state)
        assert first_day in state.days_covered

    def test_process_no_followup_advances_topic(self):
        from interview.question_engine import process_llm_response
        state = self._make_state()
        initial_index = state.topic_index
        raw = '{"reply": "Good answer.", "wants_followup": false, "followup_reason": ""}'
        process_llm_response(raw, state)
        # Topic should be closed and index advanced
        assert state.topic_index == initial_index + 1
        assert state.topic_states[initial_index].is_complete is True

    def test_process_followup_stays_on_topic(self):
        from interview.question_engine import process_llm_response
        state = self._make_state()
        initial_index = state.topic_index
        # First topic has max_followups >= 1 (FAILED/SKIPPED topics get 2)
        ts = state.topic_states[initial_index]
        ts.topic.max_followups = 2   # ensure followup is possible
        raw = '{"reply": "Can you elaborate?", "wants_followup": true, "followup_reason": "vague"}'
        process_llm_response(raw, state)
        assert state.topic_index == initial_index  # same topic
        assert ts.followups_asked == 1

    def test_process_followup_exhausted_advances_topic(self):
        from interview.question_engine import process_llm_response
        state = self._make_state()
        initial_index = state.topic_index
        ts = state.topic_states[initial_index]
        ts.topic.max_followups = 1
        ts.followups_asked = 1  # already at max
        raw = '{"reply": "Follow-up?", "wants_followup": true, "followup_reason": "need more"}'
        process_llm_response(raw, state)
        # Can't follow up — should advance
        assert state.topic_index == initial_index + 1

    def test_topics_completed_increments_when_topic_closed(self):
        from interview.question_engine import process_llm_response
        state = self._make_state()
        raw = '{"reply": "Next.", "wants_followup": false, "followup_reason": ""}'
        process_llm_response(raw, state)
        assert state.topics_completed == 1

    def test_is_done_not_set_below_floor(self):
        from interview.question_engine import process_llm_response
        state = self._make_state()
        raw = '{"reply": "Q?", "wants_followup": false, "followup_reason": ""}'
        result = process_llm_response(raw, state)
        # One question asked, far below MIN_QUESTIONS=8
        assert result.is_done is False

    def test_is_done_set_when_all_conditions_met(self):
        from interview.question_engine import process_llm_response, record_question_asked
        from planner.models import MIN_QUESTIONS, MIN_DISTINCT_DAYS
        state = self._make_state()
        # Simulate having asked enough questions and covered enough days
        state.total_questions_asked = MIN_QUESTIONS - 1  # one more will push over
        for d in list(CURRICULUM_BY_DAY.keys())[:MIN_DISTINCT_DAYS]:
            state.days_covered.add(d)
        # Close all topics except current
        for i, ts in enumerate(state.topic_states):
            if i < state.topic_index:
                ts.is_complete = True
        # This response has no followup → closes current topic
        raw = '{"reply": "Done.", "wants_followup": false, "followup_reason": ""}'
        result = process_llm_response(raw, state)
        assert result.is_done is True

    def test_cannot_complete_at_7_questions(self):
        """
        Regression test: Verify process_llm_response() never returns is_done=True
        when total_questions_asked < 8, even when wants_followup=False on every turn.
        """
        from interview.question_engine import process_llm_response
        from planner.models import MIN_QUESTIONS
        state = self._make_state()
        raw_no_followup = '{"reply": "Question text", "wants_followup": false, "followup_reason": ""}'

        for turn in range(1, MIN_QUESTIONS):
            result = process_llm_response(raw_no_followup, state)
            assert result.is_done is False, f"Interview prematurely completed at question {state.total_questions_asked}"
            assert state.total_questions_asked == turn

        assert state.total_questions_asked == 7
        assert state.is_done is False


# ---------------------------------------------------------------------------
# Prompt Builder Tests
# ---------------------------------------------------------------------------

class TestPromptBuilder:
    def setup_method(self):
        from interview.session_store import clear_all
        clear_all()

    def _make_state(self):
        from interview.session_store import create_session
        plan = _build_plan()
        return create_session("s1", CANDIDATE_GERALD, plan)

    def test_build_turn_messages_has_system_first(self):
        from interview.prompt_builder import build_turn_messages
        state = self._make_state()
        msgs = build_turn_messages(state)
        assert msgs[0]["role"] == "system"

    def test_system_message_contains_candidate_name(self):
        from interview.prompt_builder import build_turn_messages
        state = self._make_state()
        msgs = build_turn_messages(state)
        assert "Gerald Combs" in msgs[0]["content"]

    def test_system_message_contains_job_role(self):
        from interview.prompt_builder import build_turn_messages
        state = self._make_state()
        msgs = build_turn_messages(state)
        assert "IT Support Specialist" in msgs[0]["content"]

    def test_history_included_in_messages(self):
        from interview.prompt_builder import build_turn_messages
        state = self._make_state()
        state.history = [
            {"role": "assistant", "content": "What is an embedding?"},
            {"role": "user",      "content": "It converts text to vectors."},
        ]
        msgs = build_turn_messages(state)
        roles = [m["role"] for m in msgs]
        assert "assistant" in roles
        assert "user" in roles

    def test_build_feedback_messages_has_system_first(self):
        from interview.prompt_builder import build_feedback_messages
        state = self._make_state()
        msgs = build_feedback_messages(state)
        assert msgs[0]["role"] == "system"
        assert "JSON" in msgs[0]["content"]

    def test_build_feedback_messages_has_user_second(self):
        from interview.prompt_builder import build_feedback_messages
        state = self._make_state()
        msgs = build_feedback_messages(state)
        assert len(msgs) == 2
        assert msgs[1]["role"] == "user"

    def test_feedback_user_message_contains_candidate_name(self):
        from interview.prompt_builder import build_feedback_messages
        state = self._make_state()
        msgs = build_feedback_messages(state)
        assert "Gerald Combs" in msgs[1]["content"]

    def test_turn_messages_is_list_of_dicts(self):
        from interview.prompt_builder import build_turn_messages
        state = self._make_state()
        msgs = build_turn_messages(state)
        assert isinstance(msgs, list)
        for m in msgs:
            assert "role" in m
            assert "content" in m


# ---------------------------------------------------------------------------
# POST /api/interview integration tests (mock LLM)
# ---------------------------------------------------------------------------

MOCK_TURN_RESPONSE = json.dumps({
    "reply": "Can you explain what a vector embedding is?",
    "wants_followup": False,
    "followup_reason": "",
})

MOCK_FEEDBACK_RESPONSE = json.dumps({
    "summary": "Gerald showed solid foundational knowledge.",
    "strengths": ["Understood embeddings conceptually"],
    "gaps": ["Struggled with vector database internals"],
    "next": ["Review ChromaDB documentation"],
})


def _make_client():
    """Return a TestClient with the real app, LLM factory mocked."""
    from main import app
    return TestClient(app)


def _mock_llm_turn():
    """Context manager that patches get_llm_provider for turn responses."""
    from llm.mock_provider import MockProvider
    mock = MockProvider(response=MOCK_TURN_RESPONSE)
    return patch("routers.interview.get_llm_provider", return_value=mock)


def _mock_llm_all(turn_resp=None, feedback_resp=None):
    """
    Patch get_llm_provider to return a mock that returns turn_resp first
    and feedback_resp on subsequent calls (for feedback generation).
    """
    from llm.mock_provider import MockProvider
    turn = turn_resp or MOCK_TURN_RESPONSE
    feedback = feedback_resp or MOCK_FEEDBACK_RESPONSE

    call_count = {"n": 0}
    mock = MagicMock()

    def _chat(messages, json_mode=False, temperature=0.7):
        from llm.base import LLMResponse
        call_count["n"] += 1
        # First call is the turn question; use feedback JSON for later calls
        resp = turn if call_count["n"] == 1 else feedback
        return LLMResponse(content=resp, usage={}, model="mock", provider="mock")

    mock.chat = _chat
    return patch("routers.interview.get_llm_provider", return_value=mock)


INIT_PAYLOAD = {
    "sessionId": "test-session-api",
    "candidate": {
        "member": {"id":"CAND-010","name":"Gerald Combs","jobRole":"IT Support Specialist",
                   "yearsExperience":20,"education":"AAS Information Technology","status":"COMPLETED"},
        "missions": [
            {"day":7,  "title":"Embeddings Explained",           "passed":True,  "attempts":5},
            {"day":8,  "title":"Vector Databases Overview",      "passed":False, "attempts":4},
            {"day":10, "title":"Retrieval & Matching Engine",    "passed":False, "attempts":3},
            {"day":12, "title":"Prompt Engineering",             "passed":True,  "attempts":5},
            {"day":16, "title":"Chatbot Backend & API",          "passed":True,  "attempts":4},
            {"day":22, "title":"Multi-Agent Orchestration",      "passed":False, "attempts":3},
            {"day":28, "title":"Docker & Kubernetes Deployment", "skipped":True},
            {"day":31, "title":"Capstone Project",               "passed":True,  "attempts":3},
        ],
        "signals":{"commitDays":22,"missionsCompleted":23,"missionsFirstTry":1},
    }
}


class TestAPIFlow:
    def setup_method(self):
        from interview.session_store import clear_all
        clear_all()

    def test_init_returns_200_and_reply(self):
        client = _make_client()
        with _mock_llm_turn():
            resp = client.post("/api/interview", json=INIT_PAYLOAD)
        assert resp.status_code == 200
        body = resp.json()
        assert "reply" in body
        assert body["done"] is False

    def test_init_reply_is_non_empty(self):
        client = _make_client()
        with _mock_llm_turn():
            resp = client.post("/api/interview", json=INIT_PAYLOAD)
        assert len(resp.json()["reply"]) > 0

    def test_init_progress_fields_present(self):
        client = _make_client()
        with _mock_llm_turn():
            resp = client.post("/api/interview", json=INIT_PAYLOAD)
        body = resp.json()
        assert body["total_questions_asked"] == 1
        assert body["topics_completed"] is not None
        assert body["days_covered"] is not None

    def test_missing_candidate_and_message_returns_400(self):
        client = _make_client()
        resp = client.post("/api/interview", json={"sessionId": "s99"})
        assert resp.status_code == 400

    def test_continue_unknown_session_returns_400(self):
        client = _make_client()
        resp = client.post("/api/interview", json={"sessionId": "nonexistent", "message": "hello"})
        assert resp.status_code == 400

    def test_continuation_increments_question_count(self):
        client = _make_client()
        with _mock_llm_turn():
            client.post("/api/interview", json=INIT_PAYLOAD)
            resp2 = client.post("/api/interview", json={
                "sessionId": "test-session-api",
                "message": "A vector embedding converts text into numbers.",
            })
        body = resp2.json()
        assert body["total_questions_asked"] == 2

    def test_continuation_maintains_done_false(self):
        client = _make_client()
        with _mock_llm_turn():
            client.post("/api/interview", json=INIT_PAYLOAD)
            resp2 = client.post("/api/interview", json={
                "sessionId": "test-session-api",
                "message": "My answer here.",
            })
        assert resp2.json()["done"] is False

    def test_completed_session_returns_400_on_retry(self):
        from interview.session_store import get_session
        client = _make_client()
        with _mock_llm_turn():
            client.post("/api/interview", json=INIT_PAYLOAD)
        # Force session to done state
        state = get_session("test-session-api")
        if state:
            state.is_done = True
        resp = client.post("/api/interview", json={
            "sessionId": "test-session-api",
            "message": "another message",
        })
        assert resp.status_code == 400

    def test_feedback_shape_when_done(self):
        """
        Simulate reaching the completion threshold and verify the response
        has the correct feedback shape.
        """
        from interview.session_store import get_session
        from planner.models import MIN_QUESTIONS, MIN_DISTINCT_DAYS

        client = _make_client()
        with _mock_llm_turn():
            client.post("/api/interview", json=INIT_PAYLOAD)

        # Manually force the session to completion threshold
        state = get_session("test-session-api")
        assert state is not None
        state.total_questions_asked = MIN_QUESTIONS
        for d in list(CURRICULUM_BY_DAY.keys())[:MIN_DISTINCT_DAYS]:
            state.days_covered.add(d)
        # Close all topic states
        for ts in state.topic_states:
            ts.is_complete = True
        state.topic_index = len(state.topic_states)

        with _mock_llm_all(feedback_resp=MOCK_FEEDBACK_RESPONSE):
            resp = client.post("/api/interview", json={
                "sessionId": "test-session-api",
                "message": "My final answer.",
            })

        body = resp.json()
        assert body["done"] is True
        assert "feedback" in body
        fb = body["feedback"]
        assert "summary" in fb
        assert isinstance(fb["strengths"], list)
        assert isinstance(fb["gaps"], list)
        assert isinstance(fb["next"], list)

    def test_response_shape_matches_spec(self):
        """Verify every response has exactly the spec-required fields."""
        client = _make_client()
        with _mock_llm_turn():
            resp = client.post("/api/interview", json=INIT_PAYLOAD)
        body = resp.json()
        assert "reply" in body
        assert "done" in body
        assert isinstance(body["reply"], str)
        assert isinstance(body["done"], bool)
