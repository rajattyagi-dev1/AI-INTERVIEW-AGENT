# AI Usage / Vibe-Coding Log

**Project:** AI Interview Agent  
**Hackathon:** 48-hour vibe-coding hackathon  
**Problem Statement:** #2 — The Interview Agent  
**Log format:** One entry per implementation task, documenting prompts, AI actions, errors, resolutions, and human decisions.

---

## Task 1 — Project Scaffolding

### Objective

Create the foundational project structure for the AI Interview Agent:
- FastAPI backend with a placeholder `POST /api/interview` endpoint
- React + Vite + TypeScript frontend with a placeholder UI
- Clear backend/frontend separation
- Environment configuration without committing secrets
- Pydantic API schemas matching the technical specification
- Data loader for `curriculum.json` and `candidates.json`
- Vite dev-server proxy routing `/api` to the FastAPI backend

No interview logic, LLM integration, question engine, state machine, feedback generation, or polished UI were to be implemented in this task.

---

### Prompt That Initiated Task 1

The following prompt was submitted to Kiro to begin implementation:

> We are building the AI Interview Agent for the hackathon.
>
> Before making any changes, inspect the existing project, especially:
> - data/
> - docs/
>
> The provided curriculum, candidate profiles, and technical specification are authoritative hackathon resources. Do not modify or replace them.
>
> We will implement the project incrementally.
>
> For the first step, create ONLY an implementation plan for Task 1: Project Scaffolding.
>
> The target architecture is:
> - FastAPI backend
> - React + Vite + TypeScript frontend
> - backend and frontend clearly separated
> - simple hackathon-friendly architecture
> - no Redis, no microservices, no LangChain, no unnecessary infrastructure
> - environment configuration without committing secrets
> - preserve the existing data/ and docs/ directories
>
> The final backend must expose: POST /api/interview
>
> For the interview state, remember this important requirement:
> - total_questions_asked
> - topics_completed
> - days_covered
> must be tracked separately. Every interviewer question, including follow-up questions, counts toward total_questions_asked.
>
> The interview cannot finish until:
> - total_questions_asked >= 8
> - at least 4 distinct curriculum days are covered
> - the current topic is complete
>
> For Task 1, DO NOT implement interview logic, LLM integration, question selection, state machine, feedback generation, or the polished frontend.
>
> Only analyze the existing project and propose the scaffolding.
>
> Show:
> 1. Proposed directory structure
> 2. Files that will be created
> 3. Files that will remain untouched
> 4. Technologies/dependencies required
> 5. Commands needed to run backend and frontend
> 6. Any assumptions or potential issues
>
> Do not make any file changes yet. Wait for approval.

---
### Human Decision

Reviewed the proposed Task 1 plan and approved implementation.

### Implementation Summary

Created the initial FastAPI and React/TypeScript project structure,
including API schemas, data loading, environment configuration,
frontend API wrapper, and Vite proxy.

The provided `data/` and `docs/` resources were left untouched.

### Issues Resolved

- Python 3.14 caused a `pydantic-core` build problem → recreated the
  virtual environment using Python 3.12.
- Vite's interactive scaffolding timed out → frontend structure was
  completed manually.
- Port 5173 was already occupied → Vite used port 5174 and the API
  proxy continued working.

### Verification

- `GET /health` → successful
- `POST /api/interview` initialization → successful
- `POST /api/interview` continuation → successful
- Invalid request → correctly returned HTTP 400
- Frontend → HTTP 200
- Vite `/api` proxy → successfully reached FastAPI

### Task 1 Status

Complete.





---

## Task 2 — Candidate-Aware Interview Planning Layer

### Objective

Build a deterministic backend planning layer that converts a candidate profile and the curriculum into a structured interview plan. The planner must use the actual fields present in `candidates.json` and `curriculum.json`, support eventual interview requirements (≥8 questions, ≥4 distinct days), and include unit tests. No LLM, no conversation generation, no adaptive follow-ups, no feedback generation, no frontend changes.

---

### Prompt That Initiated Task 2

The following prompt was submitted to Kiro:

> Task 2 — Build the candidate-aware interview planning layer.
>
> First inspect: data/curriculum.json, data/candidates.json, docs/technical-spec.md, the files created during Task 1, and the existing PROMPTS.md.
>
> Do NOT modify data/ or docs/.
>
> Implement ONLY Task 2. Build a deterministic backend planning layer that converts a candidate profile and the curriculum into a structured interview plan for the future interview engine.
>
> The planner must use the ACTUAL fields present in candidates.json and curriculum.json. It should determine: completed curriculum days/topics, skipped topics, failed/attempt information if present, learning signals, candidate role, experience and education where available, prioritized topics for assessment, suitable difficulty/assessment strategy.
>
> The planner must support the eventual requirement of: at least 8 interviewer questions, at least 4 distinct curriculum days, questions based on concepts the candidate has completed, adaptive follow-up questions later.
>
> For this task: use deterministic logic, create structured planner models, add unit tests, do NOT implement the LLM, do NOT implement conversation generation, do NOT implement adaptive follow-ups, do NOT implement final feedback, do NOT implement frontend polish, do NOT add a database, Redis, LangChain, or unnecessary infrastructure, do NOT modify the provided hackathon resources.
>
> After implementation: run all relevant tests, report the test results, show files created/modified, explain which real candidate/curriculum fields were used, append an accurate Task 2 entry to the EXISTING root PROMPTS.md, and STOP.

---

### Human Decisions and Approvals

Kiro performed a pre-implementation context-gathering pass, reading the full contents of `curriculum.json`, `candidates.json`, and the Task 1 backend files before writing any code. This confirmed the exact field shapes (three distinct mission shapes: passed+attempts, failed+attempts, skipped-only), the full range of candidate signals, module structure, and day type values.

No separate plan approval step was required for this task — the prompt was sufficiently specific to proceed directly to implementation.

---
### Human Decision

Approved Task 2 implementation after reviewing the scope.
The implementation was required to remain deterministic and use
the provided hackathon data rather than invented fields.

### Implementation Summary

Kiro created:

- `backend/planner/models.py`
- `backend/planner/scoring.py`
- `backend/planner/builder.py`
- `backend/tests/test_scoring.py`
- `backend/tests/test_builder.py`

The planner scores candidate missions, calibrates difficulty,
selects topics, ensures curriculum-day coverage, and guarantees
enough question capacity.

### Issues Resolved

- All-mastered candidates initially produced fewer than 8 estimated
  questions → added question-floor handling.
- Sparse candidates did not always reach the required topic coverage
  → expanded fallback pillar days.
- Fixed an omitted `MIN_QUESTIONS` import.
- Fixed a syntax error introduced during editing.
- Corrected an incorrect test assumption.

### Verification

`116 passed, 0 failed`

### Task 2 Status

Complete.

---

## Task 3 — LLM Provider Abstraction

### Objective

Build a provider abstraction layer so the interview engine can call any LLM without knowing which provider is in use. Implement the OpenAI provider as the real implementation, add Groq and Anthropic stubs (no new dependencies), create a factory driven by environment variables, and add unit tests for all behaviour. No interview logic, no session state, no frontend changes.

---

### Prompt That Initiated Task 3

The following prompt was submitted to Kiro:

> Task 3 — LLM Provider Abstraction
>
> Before making any changes, inspect: data/, docs/technical-spec.md, existing backend/, existing planner/, PROMPTS.md.
>
> Do not modify data/ or docs/.
>
> Implement ONLY the LLM provider abstraction layer.
>
> Requirements:
> 1. Create a small provider interface/protocol that exposes a chat() method.
> 2. Define a common message/response structure so the interview engine can use an LLM without knowing which provider is being used.
> 3. Implement the OpenAI provider as the real provider.
> 4. Add stub providers for Anthropic and Groq only if they fit the existing architecture. They must not introduce unnecessary dependencies.
> 5. Create a provider factory that selects the provider using: LLM_PROVIDER
> 6. Support configuration through environment variables: LLM_PROVIDER, LLM_MODEL, LLM_API_KEY
> 7. Keep real secrets in the existing gitignored .env. Do not write any real API key into source code or tracked files.
> 8. Add/update .env.example with placeholder values only.
> 9. Add unit tests for: provider interface/response structure, factory provider selection, unknown provider handling, mock provider behaviour, missing API key/configuration handling where appropriate.
> 10. Do NOT implement: question generation, prompt builder, interview state machine, session store, adaptive follow-ups, feedback generation, frontend changes, database, Redis, LangChain, unnecessary infrastructure.
> 11. Do not modify the existing Task 1 or Task 2 planner behaviour.
> 12. Run the complete backend test suite after implementation and report: tests passed, tests failed, any errors and how they were fixed.
> 13. Append a concise Task 3 entry to PROMPTS.md.
>
> Then STOP.

### Result

Task 3 was completed successfully.

- OpenAI provider implemented using the OpenAI SDK.
- Groq provider added using the OpenAI-compatible API.
- Anthropic provider kept as a stub.
- Mock provider added for deterministic testing.
- Provider factory and environment-based configuration added.
- `.env.example` updated with placeholder configuration.
- No interview logic, frontend changes, or session-state logic were added.

### Verification

- **177 tests passed**
- **0 tests failed**
- Python 3.12.4
- pytest 8.3.4

During testing, a mocking issue was encountered because `patch()` was initially targeting the wrong location. It was corrected to patch the imported name where it is actually used.

### Human Decision

Task 3 was reviewed after the complete test suite passed. The implementation was accepted and the project was moved forward to Task 4

---

## Task 4 — Core Interview Engine

### Objective

Implement the core interview flow:

- Session state management
- Question engine
- Prompt builder
- `POST /api/interview` continuation flow
- Interview completion rules
- Unit tests

### Prompt Used

> Continue Task 4 using the existing planner, models, and LLM provider abstraction.
> Implement session state, question engine, prompt builder, and `/api/interview` continuation.
> Track total questions, completed topics, and curriculum days separately.
> The interview must not finish before 8 questions, 4 distinct curriculum days, and completion of the current topic.
> Add tests and run the full backend test suite.
> Do not modify `data/`, `docs/`, planner behaviour, or frontend.

### Implementation & Human Decision

Kiro created the core interview files and API integration. A completion-condition test initially failed (`39 passed, 1 failed`). I reviewed the state transition and fixed the completion logic manually.

### Result

**217 backend tests passed, 0 failed.**

---


### Additional Fix — Minimum Question Enforcement

During end-to-end testing, the interview was completing at 7 questions even though the required minimum was 8. The planner had enough follow-up capacity, but the question engine could exhaust topics before reaching the minimum.

The question engine was updated to enforce the minimum-question requirement, with a regression test added.

**Result:** 41 interview tests passed and the real API was verified to complete at exactly 8 questions, covering 6 curriculum days.
