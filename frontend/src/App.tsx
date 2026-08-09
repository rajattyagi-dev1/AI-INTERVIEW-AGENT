/**
 * App.tsx — Complete AI Technical Interview Interface.
 *
 * Implements the full end-to-end user flow:
 *   1. Welcome / candidate card screen
 *   2. Session initialization via POST /api/interview
 *   3. Interactive dark chat UI with progress bar
 *   4. Turn-by-turn answer submission with error handling
 *   5. Completion screen with executive summary, strengths, gaps & recommendations
 */

import { useState, useRef, useEffect } from "react";
import { postInterview, InterviewApiError } from "./api/interview";
import type { Candidate, Feedback, InterviewResponse } from "./types/interview";
import "./App.css";

// STUB_CANDIDATE provided by Task 1 / scaffolding specs
const STUB_CANDIDATE: Candidate = {
  member: {
    id: "CAND-001",
    name: "Sarah Johnson",
    jobRole: "Senior Data Engineer",
    yearsExperience: 9,
    education: "MS Computer Science",
    status: "COMPLETED",
  },
  missions: [
    { day: 7, title: "Embeddings Explained", passed: true, attempts: 1 },
    { day: 12, title: "Prompt Engineering Fundamentals", passed: true, attempts: 4 },
  ],
  signals: { commitDays: 28, missionsCompleted: 30, missionsFirstTry: 20 },
};

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

export default function App() {
  const [screen, setScreen] = useState<"welcome" | "interview" | "complete">("welcome");
  const [sessionId, setSessionId] = useState<string>("");
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

  // Handler: Start a new interview session
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
        candidate: STUB_CANDIDATE,
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
              Welcome to your technical interview. This AI agent assesses your understanding
              of the AI Cohort curriculum, adapting to your specific learning path, passed missions,
              and areas needing depth.
            </p>
          </div>

          <div className="candidate-profile-box">
            <div className="candidate-profile-header">
              <div className="candidate-avatar">SJ</div>
              <div className="candidate-name-role">
                <h3>{STUB_CANDIDATE.member.name}</h3>
                <p>{STUB_CANDIDATE.member.jobRole}</p>
              </div>
            </div>

            <div className="candidate-details-grid">
              <div className="detail-item">
                <span className="detail-label">Experience</span>
                <span className="detail-value">{STUB_CANDIDATE.member.yearsExperience} Years</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Education</span>
                <span className="detail-value">{STUB_CANDIDATE.member.education}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Missions Completed</span>
                <span className="detail-value">{STUB_CANDIDATE.signals.missionsCompleted} Missions</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Commit Days</span>
                <span className="detail-value">{STUB_CANDIDATE.signals.commitDays} Days</span>
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
                    {msg.role === "interviewer" ? "AI" : "SJ"}
                  </div>
                  <div className="msg-body">
                    <div className="msg-header">
                      {msg.role === "interviewer" ? "AI Interviewer" : STUB_CANDIDATE.member.name}
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
