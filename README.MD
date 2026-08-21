# 🤖 AI Interview Agent

### Personalized • Adaptive • Multi-Turn Technical Interviews

An AI-powered technical interview agent that transforms a candidate's **31-day AI learning journey** into a realistic, personalized technical interview.

Instead of asking a fixed list of questions, the agent uses the candidate's progress, learning signals, curriculum objectives, and previous answers to decide **what to ask next**.

<br>

[![Live Demo](https://img.shields.io/badge/🚀%20Live%20Demo-Vercel-black?style=for-the-badge)](https://ai-interview-agent-ikhyfso8j-rajat-tyagis-projects-f5907e70.vercel.app)
[![Backend](https://img.shields.io/badge/⚡%20Backend-Render-46E3B7?style=for-the-badge)](https://ai-interview-agent-backend-lmou.onrender.com/health)
[![GitHub](https://img.shields.io/badge/💻%20GitHub-Repository-181717?style=for-the-badge&logo=github)](https://github.com/rajattyagi-dev1/AI-INTERVIEW-AGENT)

---

## 🎯 Why This Project?

Traditional interview preparation often relies on static question banks.

That approach doesn't answer an important question:

> **What should this candidate be asked next based on what they actually learned and how they performed?**

The AI Interview Agent solves this by combining:

**Candidate Profile + Curriculum + Learning Signals + Conversation History**

to create an adaptive interview experience.

---

## ✨ Highlights

| Capability                    | What it does                                                             |
| ----------------------------- | ------------------------------------------------------------------------ |
| 🎯 **Personalized Planning**  | Builds an interview plan from the candidate's learning journey           |
| 🧠 **Adaptive Questions**     | Generates questions based on curriculum objectives and candidate signals |
| 🔄 **Intelligent Follow-ups** | Probes vague, incomplete, or technically interesting answers             |
| 🚫 **Non-Repetitive Flow**    | Varies conceptual angles and avoids repeating questions                  |
| 🗺️ **Topic Transitions**      | Explicitly pivots between curriculum topics                              |
| 💬 **Multi-Turn Context**     | Maintains conversation history throughout the interview                  |
| 👥 **Candidate Selection**    | Supports all supplied candidate profiles                                 |
| 📊 **Structured Feedback**    | Produces strengths, gaps, summary, and next steps                        |
| 🛡️ **429 Handling**           | Gracefully handles LLM rate-limit/quota errors                           |
| 🔁 **Retry Protection**       | Prevents duplicate submissions during retries                            |

---

## 🧠 How It Works

```text
┌──────────────────────┐
│   Candidate Profile  │
│ Missions • Attempts  │
│ Signals • Progress   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Interview Planner   │
│                      │
│ Selects curriculum   │
│ topics + difficulty  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│    Question Engine   │
│                      │
│ Context + objectives │
│ + previous answers   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│      Gemini LLM      │
│                      │
│ Question / Follow-up │
└──────────┬───────────┘
           │
           ▼
      Candidate Answer
           │
           ▼
┌──────────────────────┐
│   Adaptive Decision  │
│                      │
│ Follow up OR pivot   │
│ to another topic     │
└──────────┬───────────┘
           │
           ▼
      Final Feedback
```

---

## 🏗️ Production Architecture

```text
                    ┌───────────────────────┐
                    │        Vercel         │
                    │    React + Vite       │
                    └───────────┬───────────┘
                                │
                         HTTPS / REST API
                                │
                                ▼
                    ┌───────────────────────┐
                    │        Render         │
                    │       FastAPI         │
                    ├───────────────────────┤
                    │ Interview Router      │
                    │ Session State         │
                    │ Planner               │
                    │ Question Engine       │
                    │ Prompt Builder        │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │      Gemini API       │
                    │   Question Generation │
                    │   Follow-ups          │
                    │   Final Feedback      │
                    └───────────────────────┘
```

### Data Flow

```text
Candidate Profile
       ↓
Interview Plan
       ↓
Curriculum Topic
       ↓
LLM-generated Question
       ↓
Candidate Answer
       ↓
Context-aware Follow-up
       │
       └──────→ New Topic
                    ↓
             Next Interview Turn
                    ↓
             Structured Feedback
```

---

## 👥 Candidate Personalization

The application uses the **supplied candidate profiles** rather than relying on a single hardcoded interviewee.

A candidate can be selected directly from the welcome screen.

The selected profile influences the interview through information such as:

- Completed missions
- Mission status
- Attempts
- Skipped topics
- Learning signals
- Experience
- Education
- Curriculum progress

This allows the same interview agent to produce different interview experiences for different candidates.

---

## 🔄 Adaptive Interviewing

The agent is explicitly designed to avoid becoming a scripted questionnaire.

### Question variation

The interviewer is instructed to:

- Ask one question at a time
- Avoid repeating previously asked questions
- Vary the conceptual angle
- Cover different curriculum objectives
- Use the candidate's previous answer to determine the next step

### Follow-up logic

```text
Candidate Answer
      │
      ├── Vague / Incomplete
      │        ↓
      │   Targeted Follow-up
      │
      ├── Interesting / Partially Correct
      │        ↓
      │   Deeper Probe
      │
      └── Satisfactory
               ↓
          New Aspect / Topic
```

---

## 📋 Interview Requirements

The implementation is designed to satisfy the core challenge requirements:

- ✅ Conversational technical interview
- ✅ Minimum 8 questions
- ✅ Questions across multiple curriculum days
- ✅ Context-aware follow-ups
- ✅ Multi-turn conversation state
- ✅ Structured final feedback
- ✅ Required HTTP API endpoint
- ✅ Personalized candidate experience

The interview flow was verified with **8 questions across 6 curriculum days** during development.

---

## 📊 Final Feedback

At the end of the interview, the agent generates structured feedback containing:

```json
{
  "summary": "Overall assessment",
  "strengths": ["Strength 1", "Strength 2"],
  "gaps": ["Gap 1", "Gap 2"],
  "next": ["Recommended next step 1", "Recommended next step 2"]
}
```

This turns the interview into an actionable learning tool rather than simply a question-answer session.

---

## 🛡️ Reliability

The system also handles real-world API failure scenarios.

### LLM Rate Limits

Gemini quota/rate-limit errors are converted into a clean:

```text
HTTP 429
```

response instead of an unhandled backend `500`.

### Retry Protection

The frontend prevents:

- Concurrent answer submissions
- Duplicate candidate messages
- Duplicate history entries during retries

This keeps the interview state consistent when the external LLM provider temporarily rejects a request.

---

## 🧪 Testing & Verification

### Backend

```bash
pytest
```

Latest verification:

```text
231 passed
0 failed
```

### Frontend

```bash
npm run build
```

Result:

```text
✓ 33 modules transformed
✓ Production build successful
```

### Production Health Check

The deployed backend successfully reported:

```json
{
  "status": "ok",
  "candidates_loaded": 20,
  "curriculum_days_loaded": 31
}
```

This confirms that the production backend successfully loads the supplied candidate profiles and complete 31-day curriculum.

---

## 🛠️ Tech Stack

### Frontend

- React
- TypeScript
- Vite
- CSS

### Backend

- Python
- FastAPI
- Pydantic
- Uvicorn
- Pytest

### AI

- Gemini API
- Custom LLM provider abstraction
- Prompt engineering
- Adaptive interview orchestration

### Deployment

- Vercel
- Render

---

## 📁 Project Structure

```text
AI-INTERVIEW-AGENT/
│
├── backend/
│   ├── data/
│   ├── interview/
│   ├── llm/
│   ├── models/
│   ├── planner/
│   ├── routers/
│   ├── tests/
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   └── types/
│   ├── package.json
│   ├── vite.config.ts
│   └── .env.example
│
├── data/
├── docs/
├── PROMPTS.md
├── README.md
└── .gitignore
```

---

## 🚀 Run Locally

### Backend

```bash
cd backend

python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `.env` from `.env.example` and configure your Gemini API credentials.

Start the API:

```bash
uvicorn main:app --reload --port 8000
```

### Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at:

```text
http://localhost:5173
```

The local Vite proxy forwards:

```text
/api/*
      ↓
http://localhost:8000
```

---

## 🔐 Environment Variables

### Backend

```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.6-flash
LLM_API_KEY=your_gemini_api_key
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### Frontend

```env
VITE_API_BASE_URL=https://your-render-backend-url
```

Never commit real API keys or `.env` files.

---

## 🌐 Deployment

### Frontend

Deployed with **Vercel**.

### Backend

Deployed with **Render**.

The production architecture separates the frontend and backend while keeping the API endpoint configurable through environment variables.

---

## 📚 AI Usage & Development Log

AI-assisted development was used throughout the project for:

- Architecture exploration
- Implementation
- Debugging
- Test creation
- Prompt engineering
- Interview-flow refinement
- Rate-limit handling
- Deployment configuration

The complete AI-assisted development history is documented in:

👉 **[PROMPTS.md](./PROMPTS.md)**

---

## 🎥 Demo

The live application allows a user to:

1. Select a candidate profile
2. Start a personalized interview
3. Answer technical questions
4. Receive adaptive follow-ups
5. Move across curriculum topics
6. Complete the interview
7. Receive structured technical feedback

---

## 🔗 Links

| Resource          | Link                                                                           |
| ----------------- | ------------------------------------------------------------------------------ |
| 🚀 Live Demo      | https://ai-interview-agent-ikhyfso8j-rajat-tyagis-projects-f5907e70.vercel.app |
| ⚡ Backend Health | https://ai-interview-agent-backend-lmou.onrender.com/health                    |
| 💻 GitHub         | https://github.com/rajattyagi-dev1/AI-INTERVIEW-AGENT                          |
| 🤖 AI Usage Log   | https://github.com/rajattyagi-dev1/AI-INTERVIEW-AGENT/blob/main/PROMPTS.md     |

---

## 👨‍💻 Author

### Rajat Tyagi

Built for the **AI Cohort Interview Agent Challenge**.

> **From learning journey → to personalized technical interview.**
