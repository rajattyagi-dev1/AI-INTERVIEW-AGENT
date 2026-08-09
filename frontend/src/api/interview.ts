/**
 * Typed fetch wrapper for POST /api/interview.
 *
 * All requests go through this single function. The Vite dev-server proxy
 * forwards /api/* to http://localhost:8000, so no host is hardcoded here.
 */

import type { InterviewRequest, InterviewResponse } from "../types/interview";

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const ENDPOINT = `${BASE_URL}/api/interview`;

export class InterviewApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "InterviewApiError";
  }
}

export async function postInterview(
  payload: InterviewRequest,
): Promise<InterviewResponse> {
  const res = await fetch(ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const err = await res.json();
      detail = err.detail ?? detail;
    } catch {
      // ignore JSON parse failure on error body
    }
    throw new InterviewApiError(res.status, detail);
  }

  return res.json() as Promise<InterviewResponse>;
}
