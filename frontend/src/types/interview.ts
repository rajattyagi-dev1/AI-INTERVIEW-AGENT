/**
 * TypeScript types mirroring the backend Pydantic schemas in
 * backend/models/schemas.py and the API contract in docs/technical-spec.md.
 */

// ---------------------------------------------------------------------------
// Candidate object (mirrors candidates.json schema)
// ---------------------------------------------------------------------------

export interface CandidateMember {
  id: string;
  name: string;
  jobRole: string;
  yearsExperience: number;
  education: string;
  status: string;
}

export interface CandidateMission {
  day: number;
  title: string;
  passed?: boolean;
  attempts?: number;
  skipped?: boolean;
}

export interface CandidateSignals {
  commitDays: number;
  missionsCompleted: number;
  missionsFirstTry: number;
}

export interface Candidate {
  member: CandidateMember;
  missions: CandidateMission[];
  signals: CandidateSignals;
}

// ---------------------------------------------------------------------------
// Request
// ---------------------------------------------------------------------------

/** Case 1 — start a new interview */
export interface StartInterviewRequest {
  sessionId: string;
  candidate: Candidate;
}

/** Case 2 — continue an existing interview */
export interface ContinueInterviewRequest {
  sessionId: string;
  message: string;
}

export type InterviewRequest = StartInterviewRequest | ContinueInterviewRequest;

// ---------------------------------------------------------------------------
// Final feedback
// ---------------------------------------------------------------------------

export interface Feedback {
  summary: string;
  strengths: string[];
  gaps: string[];
  next: string[];
}

// ---------------------------------------------------------------------------
// Response
// ---------------------------------------------------------------------------

export interface InterviewResponse {
  /** The interviewer's reply to display in the chat. */
  reply: string;

  /** False during the interview; true on the final response. */
  done: boolean;

  /** Present only when done is true. */
  feedback?: Feedback;

  // --- Optional progress display fields ---
  /** Current curriculum topic title. */
  topic?: string;
  /** Current curriculum day number. */
  day?: number;
  /** Every question asked, including follow-ups. */
  total_questions_asked?: number;
  /** Topics fully closed so far. */
  topics_completed?: number;
  /** Distinct curriculum days covered so far. */
  days_covered?: number;
}
