/**
 * App.tsx — placeholder UI for Task 1 scaffolding.
 *
 * This component will be replaced with the full interview UI in Task 10.
 * For now it renders a minimal page that:
 *   1. Confirms the frontend is running.
 *   2. Lets you smoke-test the POST /api/interview endpoint via a button.
 */

import { useState } from "react";
import { postInterview, InterviewApiError } from "./api/interview";
import type { InterviewResponse } from "./types/interview";

// Minimal inline styles — Tailwind will replace these in Task 10.
const styles: Record<string, React.CSSProperties> = {
  root: {
    fontFamily: "system-ui, sans-serif",
    maxWidth: 640,
    margin: "60px auto",
    padding: "0 24px",
    color: "#1a1a2e",
  },
  header: { borderBottom: "2px solid #e2e8f0", paddingBottom: 16, marginBottom: 32 },
  title: { fontSize: 28, fontWeight: 700, margin: 0 },
  subtitle: { fontSize: 14, color: "#64748b", marginTop: 6 },
  card: {
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: 8,
    padding: 24,
    marginBottom: 24,
  },
  button: {
    background: "#3b82f6",
    color: "#fff",
    border: "none",
    borderRadius: 6,
    padding: "10px 20px",
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
    marginTop: 12,
  },
  pre: {
    background: "#1e293b",
    color: "#e2e8f0",
    borderRadius: 6,
    padding: 16,
    fontSize: 12,
    overflowX: "auto",
    marginTop: 16,
  },
  error: { color: "#dc2626", marginTop: 12, fontSize: 14 },
  badge: {
    display: "inline-block",
    background: "#dcfce7",
    color: "#166534",
    borderRadius: 4,
    padding: "2px 8px",
    fontSize: 12,
    fontWeight: 600,
    marginLeft: 8,
  },
};

// A minimal candidate fixture used only for the smoke test.
const STUB_CANDIDATE = {
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

export default function App() {
  const [response, setResponse] = useState<InterviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleTest() {
    setLoading(true);
    setError(null);
    setResponse(null);
    try {
      const res = await postInterview({
        sessionId: "test-session-001",
        candidate: STUB_CANDIDATE,
      });
      setResponse(res);
    } catch (e) {
      if (e instanceof InterviewApiError) {
        setError(`API error ${e.status}: ${e.message}`);
      } else {
        setError(String(e));
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.root}>
      <header style={styles.header}>
        <h1 style={styles.title}>
          AI Interview Agent
          <span style={styles.badge}>Scaffolding</span>
        </h1>
        <p style={styles.subtitle}>
          Task 1 placeholder — full UI coming in Task 10.
        </p>
      </header>

      <div style={styles.card}>
        <strong>Endpoint smoke test</strong>
        <p style={{ fontSize: 14, color: "#475569", margin: "8px 0 0" }}>
          Sends a <code>POST /api/interview</code> request with a stub candidate
          (CAND-001) to verify the backend is reachable.
        </p>
        <button style={styles.button} onClick={handleTest} disabled={loading}>
          {loading ? "Sending…" : "Test POST /api/interview"}
        </button>

        {error && <p style={styles.error}>{error}</p>}

        {response && (
          <pre style={styles.pre}>{JSON.stringify(response, null, 2)}</pre>
        )}
      </div>

      <div style={styles.card}>
        <strong>Backend</strong>
        <p style={{ fontSize: 14, color: "#475569", margin: "8px 0 0" }}>
          <code>http://localhost:8000</code> — FastAPI + Uvicorn
          <br />
          Swagger UI: <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">
            localhost:8000/docs
          </a>
        </p>
      </div>
    </div>
  );
}
