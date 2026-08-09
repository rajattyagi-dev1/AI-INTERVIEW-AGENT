/**
 * App.tsx — Complete AI Technical Interview Interface.
 *
 * Implements the full end-to-end user flow:
 *   1. Welcome screen with candidate profile selection from supplied candidates.json
 *   2. Session initialization via POST /api/interview
 *   3. Interactive dark chat UI with progress bar & dynamic avatar initials
 *   4. Turn-by-turn answer submission with 429 & retry handling
 *   5. Completion screen with executive summary, strengths, gaps & recommendations
 */

import { useState, useRef, useEffect } from "react";
import { postInterview, InterviewApiError } from "./api/interview";
import type { Candidate, Feedback, InterviewResponse } from "./types/interview";
import candidatesData from "../../data/candidates.json";
import "./App.css";

// Supplied candidate profiles loaded directly from data/candidates.json
const CANDIDATE_PROFILES: Candidate[] = candidatesData.candidates as Candidate[];

interface ChatMessage {
  id: string;
  role: "interviewer" | "candidate";
  content: string;
  timestamp: string;
}

function generateSessionId(): string {
  return `sess-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
}

function formatTime(): string {
  const d = new Date();
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function getInitials(name: string): string {
  if (!name) return "CA";
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
  }
  return name.substring(0, 2).toUpperCase();
}

export default function App() {
  const [screen, setScreen] = useState<"welcome" | "interview" | "complete">("welcome");
  const [sessionId, setSessionId] = useState<string>("");
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate>(CANDIDATE_PROFILES[0]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputAnswer, setInputAnswer] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Optional progress fields from InterviewResponse
  const [progress, setProgress] = useState<{
    topic?: string;
    day?: number;
    total_questions_asked?: number;
    topics_completed?: number;
    days_covered?: number;
  }>({});

  // Final feedback object when done === true
  const [feedback, setFeedback] = useState<Feedback | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll chat window when new messages arrive or loading state changes
  useEffect(() => {
    if (screen === "interview") {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, loading, screen]);

  // Handler: Start a new interview session with selected candidate profile
  async function handleStartInterview() {
    const newSessionId = generateSessionId();
    setSessionId(newSessionId);
    setMessages([]);
    setInputAnswer("");
    setError(null);
    setFeedback(null);
    setProgress({});
    setScreen("interview");
    setLoading(true);

    try {
      const res: InterviewResponse = await postInterview({
        sessionId: newSessionId,
        candidate: selectedCandidate,
      });

      const initialMsg: ChatMessage = {
        id: `msg-init-${Date.now()}`,
        role: "interviewer",
        content: res.reply,
        timestamp: formatTime(),
      };

      setMessages([initialMsg]);
      updateProgress(res);

      if (res.done) {
        if (res.feedback) setFeedback(res.feedback);
        setScreen("complete");
      }
    } catch (err) {
      handleApiError(err, "Failed to initialize interview session.");
      setScreen("welcome");
    } finally {
      setLoading(false);
    }
  }

  // Handler: Send candidate's technical answer
  async function handleSendAnswer() {
    const text = inputAnswer.trim();
    if (!text || loading) return;

    setLoading(true);
    setError(null);

    // Append candidate message if not already present from previous failed attempt
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.role === "candidate" && last.content === text) {
        return prev;
      }
      return [
        ...prev,
        {
          id: `msg-user-${Date.now()}`,
          role: "candidate",
          content: text,
          timestamp: formatTime(),
        },
      ];
    });

    setInputAnswer("");

    try {
      const res: InterviewResponse = await postInterview({
        sessionId,
        message: text,
      });

      const aiMsg: ChatMessage = {
        id: `msg-ai-${Date.now()}`,
        role: "interviewer",
        content: res.reply,
        timestamp: formatTime(),
      };

      setMessages((prev) => [...prev, aiMsg]);
      updateProgress(res);

      if (res.done) {
        if (res.feedback) setFeedback(res.feedback);
        setScreen("complete");
      }
    } catch (err) {
      handleApiError(err, "Failed to submit response.");
      // Repopulate user input so candidate doesn't lose text and can retry
      setInputAnswer(text);
    } finally {
      setLoading(false);
    }
  }

  function updateProgress(res: InterviewResponse) {
    setProgress((prev) => ({
      topic: res.topic ?? prev.topic,
      day: res.day ?? prev.day,
      total_questions_asked: res.total_questions_asked ?? prev.total_questions_asked,
      topics_completed: res.topics_completed ?? prev.topics_completed,
      days_covered: res.days_covered ?? prev.days_covered,
    }));
  }

  function handleApiError(err: unknown, defaultMsg: string) {
    if (err instanceof InterviewApiError) {
      setError(`API Error (${err.status}): ${err.message}`);
    } else if (err instanceof Error) {
      setError(err.message);
    } else {
      setError(defaultMsg);
    }
  }

  const candidateInitials = getInitials(selectedCandidate.member.name);

  return (
    <div className="app-container">
      {/* App Header */}
      <header className="app-header">
        <div className="header-brand">
          <div className="ai-logo-icon">AI</div>
          <div>
            <h1 className="app-title">AI Interview Agent</h1>
            <p className="app-subtitle">Personalized Technical Interview</p>
          </div>
        </div>
        <div className="status-badge">
          <span className={`status-dot ${screen === "interview" ? "active" : ""}`} />
          {screen === "welcome" && "Ready to Start"}
          {screen === "interview" && "Interview Active"}
          {screen === "complete" && "Assessment Complete"}
        </div>
      </header>

      {/* Screen 1: Welcome & Candidate Overview */}
      {screen === "welcome" && (
        <div className="welcome-card">
          <div className="welcome-hero">
            <h2>Personalized AI Technical Assessment</h2>
            <p>
              Welcome to your technical interview. Select a candidate profile below to begin.
              The AI agent will adapt questions based on your specific learning path, passed missions,
              and areas needing depth.
            </p>
          </div>

          {/* Candidate Profile Dropdown Selector */}
          <div className="candidate-selector-box" style={{ marginBottom: "20px" }}>
            <label
              htmlFor="candidate-select"
              style={{
                display: "block",
                marginBottom: "8px",
                fontWeight: "600",
                color: "#94a3b8",
                fontSize: "0.875rem",
              }}
            >
              Select Candidate Profile:
            </label>
            <select
              id="candidate-select"
              className="candidate-dropdown"
              value={selectedCandidate.member.id}
              onChange={(e) => {
                const found = CANDIDATE_PROFILES.find((c) => c.member.id === e.target.value);
                if (found) setSelectedCandidate(found);
              }}
              disabled={loading}
              style={{
                width: "100%",
                padding: "12px 16px",
                borderRadius: "8px",
                backgroundColor: "#1e293b",
                color: "#f8fafc",
                border: "1px solid #334155",
                fontSize: "1rem",
                cursor: "pointer",
                outline: "none",
              }}
            >
              {CANDIDATE_PROFILES.map((c) => (
                <option key={c.member.id} value={c.member.id}>
                  {c.member.name} — {c.member.jobRole} ({c.member.yearsExperience} yrs exp)
                </option>
              ))}
            </select>
          </div>

          {/* Dynamic Candidate Profile Card */}
          <div className="candidate-profile-box">
            <div className="candidate-profile-header">
              <div className="candidate-avatar">{candidateInitials}</div>
              <div className="candidate-name-role">
                <h3>{selectedCandidate.member.name}</h3>
                <p>{selectedCandidate.member.jobRole}</p>
              </div>
            </div>

            <div className="candidate-details-grid">
              <div className="detail-item">
                <span className="detail-label">Experience</span>
                <span className="detail-value">{selectedCandidate.member.yearsExperience} Years</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Education</span>
                <span className="detail-value">{selectedCandidate.member.education}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Missions Completed</span>
                <span className="detail-value">{selectedCandidate.signals.missionsCompleted} Missions</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Commit Days</span>
                <span className="detail-value">{selectedCandidate.signals.commitDays} Days</span>
              </div>
            </div>
          </div>

          {error && <div className="error-banner" style={{ margin: "0 0 20px" }}>{error}</div>}

          <button className="btn-primary" onClick={handleStartInterview} disabled={loading}>
            {loading ? "Initializing Session…" : "Start Interview →"}
          </button>
        </div>
      )}

      {/* Screen 2: Active Chat Interview Screen */}
      {screen === "interview" && (
        <>
          {/* Progress Card Header */}
          <div className="progress-card">
            <div className="progress-item">
              <span className="progress-label">Current Topic</span>
              <span className="progress-value highlight">{progress.topic || "Initializing..."}</span>
            </div>
            <div className="progress-item">
              <span className="progress-label">Day</span>
              <span className="progress-value">{progress.day !== undefined ? `Day ${progress.day}` : "—"}</span>
            </div>
            <div className="progress-item">
              <span className="progress-label">Questions</span>
              <span className="progress-value">{progress.total_questions_asked ?? 0}</span>
            </div>
            <div className="progress-item">
              <span className="progress-label">Topics Done</span>
              <span className="progress-value">{progress.topics_completed ?? 0}</span>
            </div>
            <div className="progress-item">
              <span className="progress-label">Days Covered</span>
              <span className="progress-value">{progress.days_covered ?? 0}</span>
            </div>
          </div>

          {/* Error Notification Banner */}
          {error && (
            <div className="error-banner">
              <span>{error}</span>
              <button className="retry-btn" onClick={handleSendAnswer}>Retry</button>
            </div>
          )}

          {/* Main Chat Interface */}
          <div className="chat-container">
            <div className="chat-messages">
              {messages.map((msg) => (
                <div key={msg.id} className={`chat-message ${msg.role}`}>
                  <div className={`msg-avatar ${msg.role === "interviewer" ? "ai" : "user"}`}>
                    {msg.role === "interviewer" ? "AI" : candidateInitials}
                  </div>
                  <div className="msg-body">
                    <div className="msg-header">
                      {msg.role === "interviewer" ? "AI Interviewer" : selectedCandidate.member.name}
                    </div>
                    <div className="msg-bubble">{msg.content}</div>
                    <div className="msg-time">{msg.timestamp}</div>
                  </div>
                </div>
              ))}

              {/* AI Thinking Indicator */}
              {loading && (
                <div className="chat-message interviewer">
                  <div className="msg-avatar ai">AI</div>
                  <div className="thinking-indicator">
                    <span>AI interviewer is thinking</span>
                    <div className="typing-dots">
                      <span />
                      <span />
                      <span />
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Answer Input Controls */}
            <div className="chat-input-container">
              <form
                className="chat-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendAnswer();
                }}
              >
                <textarea
                  className="chat-textarea"
                  placeholder="Type your technical response here... (Press Ctrl+Enter or click Send Answer)"
                  value={inputAnswer}
                  onChange={(e) => setInputAnswer(e.target.value)}
                  disabled={loading}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                      e.preventDefault();
                      handleSendAnswer();
                    }
                  }}
                />
                <div className="input-actions">
                  <span className="input-hint">Use Ctrl+Enter to send</span>
                  <button
                    type="submit"
                    className="btn-primary"
                    disabled={loading || !inputAnswer.trim()}
                  >
                    {loading ? "Sending..." : "Send Answer ↑"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </>
      )}

      {/* Screen 3: Completion & Feedback Screen */}
      {screen === "complete" && (
        <div className="completion-container">
          <div className="completion-hero-card">
            <span className="completion-badge">Assessment Completed</span>
            <h2 className="completion-title">Interview Complete</h2>
            <p style={{ color: "#94a3b8" }}>
              Great job! You have completed your technical interview session. Below is your detailed feedback summary.
            </p>

            <div className="completion-stats-row">
              <div className="stat-box">
                <span className="stat-num">{progress.total_questions_asked ?? 0}</span>
                <span className="stat-desc">Total Questions</span>
              </div>
              <div className="stat-box">
                <span className="stat-num">{progress.topics_completed ?? 0}</span>
                <span className="stat-desc">Topics Completed</span>
              </div>
              <div className="stat-box">
                <span className="stat-num">{progress.days_covered ?? 0}</span>
                <span className="stat-desc">Days Covered</span>
              </div>
            </div>
          </div>

          {/* Feedback Cards */}
          {feedback && (
            <>
              <div className="feedback-card">
                <h3 className="feedback-section-title">Executive Summary</h3>
                <p className="summary-text">{feedback.summary}</p>
              </div>

              <div className="feedback-grid">
                <div className="feedback-column strengths">
                  <h4 className="col-title">Strengths</h4>
                  <ul className="bullet-list">
                    {feedback.strengths.map((item, i) => (
                      <li key={i}>{item}</li>
                    ))}
                  </ul>
                </div>

                <div className="feedback-column gaps">
                  <h4 className="col-title">Areas to Improve</h4>
                  <ul className="bullet-list">
                    {feedback.gaps.map((item, i) => (
                      <li key={i}>{item}</li>
                    ))}
                  </ul>
                </div>

                <div className="feedback-column next">
                  <h4 className="col-title">Recommended Next Steps</h4>
                  <ul className="bullet-list">
                    {feedback.next.map((item, i) => (
                      <li key={i}>{item}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </>
          )}

          <div className="completion-actions">
            <button className="btn-primary" onClick={handleStartInterview}>
              Start New Interview ↻
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
