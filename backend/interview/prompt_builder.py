"""
Prompt builder for the interview engine.

Assembles the LLM message list for two distinct call types:
  1. build_turn_messages()     — generate next interviewer question/follow-up
  2. build_feedback_messages() — generate structured final feedback (JSON mode)

Both return list[dict] ready for llm_provider.chat().
"""

from __future__ import annotations

from interview.session_store import SessionState
from planner.models import DifficultyLevel, MissionLabel

# ---------------------------------------------------------------------------
# Difficulty instruction wording
# ---------------------------------------------------------------------------
_DIFFICULTY_HINT: dict[DifficultyLevel, str] = {
    DifficultyLevel.CONCEPTUAL: (
        "Focus on definitions, intuitions, and conceptual understanding. "
        "Do not assume hands-on implementation experience."
    ),
    DifficultyLevel.APPLIED: (
        "Focus on practical usage, tradeoffs, and moderate implementation depth."
    ),
    DifficultyLevel.ARCHITECTURAL: (
        "Focus on system design, architecture decisions, integration patterns, "
        "and deep technical tradeoffs."
    ),
}

_LABEL_HINT: dict[MissionLabel, str] = {
    MissionLabel.FAILED: (
        "The candidate attempted this topic but did not pass. "
        "Probe foundational understanding directly."
    ),
    MissionLabel.SKIPPED: (
        "The candidate skipped this topic. "
        "Ask conceptually — they may have no hands-on experience."
    ),
    MissionLabel.STRUGGLED: (
        "The candidate passed this topic after several attempts. "
        "Probe for depth to verify genuine understanding."
    ),
    MissionLabel.PARTIAL: (
        "The candidate passed this topic with some effort. "
        "Ask a standard depth question."
    ),
    MissionLabel.MASTERED: (
        "The candidate passed this topic on the first try. "
        "Ask an applied or higher-level question to confirm depth."
    ),
}

# ---------------------------------------------------------------------------
# System prompt template
# ---------------------------------------------------------------------------
_SYSTEM_TEMPLATE = """\
You are an expert AI technical interviewer conducting a structured interview.

Candidate: {name}
Role: {job_role}
Experience: {years} years
Education: {education}

Your job is to assess this candidate's understanding of an AI/ML curriculum
they recently completed. Be professional, concise, and conversational.

For each interviewer turn, respond with ONLY a JSON object in this exact format:
{{
  "reply": "<your question or follow-up as a string>",
  "wants_followup": <true or false>,
  "followup_reason": "<one sentence reason if wants_followup is true, else empty string>"
}}

Rules:
- Ask ONE question per turn. Never ask multiple questions at once.
- If the candidate's answer is vague or incomplete, set wants_followup to true.
- When asking a follow-up, explicitly address or clarify a specific point, claim, term, or misconception from the candidate's previous response. Use the candidate's previous answer to decide whether to probe deeper or move to a different aspect.
- Vary the conceptual angle of each question and avoid testing the same concept repeatedly.
- Cover different curriculum objectives within the current topic before repeating any area.
- If the answer is satisfactory or you have asked enough follow-ups, set wants_followup to false.
- Never reveal that you are following a plan or that follow-up limits exist.
- Keep questions under 60 words.
- Do not repeat questions already asked.
"""

# ---------------------------------------------------------------------------
# Feedback system prompt
# ---------------------------------------------------------------------------
_FEEDBACK_SYSTEM = """\
You are an expert technical interviewer writing a post-interview assessment.
Based on the interview transcript below, produce a structured JSON feedback object.

Return ONLY valid JSON matching exactly this schema:
{
  "summary": "<2-3 sentence overall assessment>",
  "strengths": ["<specific strength>", ...],
  "gaps": ["<specific gap>", ...],
  "next": ["<actionable recommendation>", ...]
}

Each array should contain 2-4 concise, specific items grounded in the transcript.
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_turn_messages(state: SessionState) -> list[dict]:
    """
    Build the message list for the next interview turn.

    Structure:
      [system prompt]
      [conversation history so far]
      [topic injection system message — only when starting a new topic]
    """
    profile = state.plan.candidate_profile

    system_content = _SYSTEM_TEMPLATE.format(
        name=profile.name,
        job_role=profile.job_role,
        years=profile.years_experience,
        education=profile.education,
    )

    messages: list[dict] = [
        {"role": "system", "content": system_content}
    ]

    # Append the full conversation history so the LLM has context
    messages.extend(state.history)

    ts = state.current_topic_state

    if ts and not ts.is_complete:
        topic = ts.topic
        diff_hint = _DIFFICULTY_HINT.get(topic.difficulty, "")
        label_hint = _LABEL_HINT.get(topic.label, "")

        # First question on this topic — add topic context
        if ts.followups_asked == 0:
            is_topic_change = len(state.history) > 0
            transition_header = (
                f"[Topic Transition — Pivot to new topic. Do not ask about prior topics.]\n"
                if is_topic_change
                else f"[Topic Context — Initial topic]\n"
            )
            topic_context = (
                f"{transition_header}"
                f"Current topic: Day {topic.day} — {topic.title}\n"
                f"Module: {topic.module_title}\n"
                f"Curriculum objectives:\n"
                + "\n".join(
                    f"  - {o}" for o in topic.objectives[:3]
                )
                + f"\nTools: {', '.join(topic.tools[:4])}\n"
                f"Assessment: {label_hint}\n"
                f"Difficulty: {diff_hint}\n"
                f"Interviewer notes: {topic.assessment_notes}\n"
                f"Focus explicitly on this current topic now. Ask your first question about Day {topic.day} — {topic.title}."
            )

            messages.append({
                "role": "system",
                "content": topic_context,
            })

    # Gemini requires a user/content turn to generate a response.
    # On the very first interview turn there is no candidate history yet.
    if not state.history:
        messages.append({
            "role": "user",
            "content": (
                "Begin the interview by asking the candidate "
                "the first technical question."
            ),
        })

    return messages


def build_feedback_messages(state: SessionState) -> list[dict]:
    """
    Build the message list for final feedback generation.
    Uses a separate system prompt and sends the full transcript as user content.
    """
    profile = state.plan.candidate_profile
    topics_covered = [
        f"Day {ts.topic.day}: {ts.topic.title} [{ts.topic.label.value}]"
        for ts in state.topic_states
        if ts.is_complete or ts.followups_asked > 0
    ]

    transcript_lines = []
    for msg in state.history:
        role = "Interviewer" if msg["role"] == "assistant" else "Candidate"
        transcript_lines.append(f"{role}: {msg['content']}")

    transcript = "\n".join(transcript_lines) if transcript_lines else "(no transcript)"

    user_content = (
        f"Candidate: {profile.name}\n"
        f"Role: {profile.job_role}\n"
        f"Experience: {profile.years_experience} years\n"
        f"Education: {profile.education}\n\n"
        f"Topics covered:\n" + "\n".join(f"  - {t}" for t in topics_covered) + "\n\n"
        f"Interview transcript:\n{transcript}"
    )

    return [
        {"role": "system", "content": _FEEDBACK_SYSTEM},
        {"role": "user",   "content": user_content},
    ]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _last_role(history: list[dict]) -> str:
    """Return the role of the last message in history, or empty string."""
    if not history:
        return ""
    return history[-1].get("role", "")
