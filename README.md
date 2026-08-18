<div align="center">

<br/>

<pre>
 ███╗   ██╗███████╗██████╗ ██╗   ██╗███████╗
 ████╗  ██║██╔════╝██╔══██╗██║   ██║██╔════╝
 ██╔██╗ ██║█████╗  ██████╔╝██║   ██║█████╗  
 ██║╚██╗██║██╔══╝  ██╔══██╗╚██╗ ██╔╝██╔══╝  
 ██║ ╚████║███████╗██║  ██║ ╚████╔╝ ███████╗
 ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝
</pre>

### **The Autonomous SRE Engine**
*From production crash to merged PR  while you sleep.*

<br/>

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-FF6B6B?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-Task_Queue-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active_Development-F59E0B?style=for-the-badge)]()

<br/>

[**View Demo**](#) · [**Report Bug**](../../issues) · [**Request Feature**](../../issues) · [**Architecture Deep Dive**](#-architecture)

</div>

---

## 🚨 The Problem

It's **2:47 AM**. Your production application just crashed. Here's what happens next:

| Step | Who Does It | Time Cost |
|------|------------|-----------|
| Alert fires, engineer gets paged | PagerDuty | ~5 min |
| Engineer wakes up, logs into Datadog/Sentry | Human | ~15 min |
| Reads the stack trace, understands context | Human | ~20 min |
| Clones repo, searches through hundreds of files | Human | ~30 min |
| Writes a fix, runs tests, submits PR | Human | ~60 min |
| PR reviewed and merged | Human | ~30 min |
| **Total MTTR** | **Everything above** | **⚡ 2-3 hours** |

This costs companies **millions in downtime**  not because engineers are slow, but because the entire process is **manually sequential**.

**Observability tools** (Datadog, Sentry) detect the fire. **AI assistants** (Copilot, ChatGPT) write code if you spoon-feed them the exact context. **Neither can autonomously bridge the gap.**

The missing link is **Autonomous Execution.**

---

## ✨ The Solution

**Nerve** is an active, multi-agent AI pipeline that mimics a senior Site Reliability Engineer.

```
  You wake up to this Slack message:

  🤖 nerve-bot   2:49 AM
  ┌─────────────────────────────────────────────────────────┐
  │  🔴 Bug Detected in production/billing.py               │
  │                                                         │
  │  Root cause: ZeroDivisionError on line 142              │
  │  Confidence: 94%                                        │
  │                                                         │
  │  ✅ Fix written & tested (3 iterations)                 │
  │  📎 Pull Request #847 is ready for your review          │
  │                                                         │
  │  [ View PR ]  [ View Agent Trace ]  [ Dismiss ]         │
  └─────────────────────────────────────────────────────────┘
```

**Instead of 3 hours  you approve a PR in 3 minutes.**

---

## 🏗️ Architecture

### System Overview

```
  [ Production Crash ]
         │
         │ 1. Webhook (Error Stack Trace + Context)
         ▼
  ┌─────────────────────┐          ┌──────────────────────────────────┐
  │   FastAPI Gateway   │◄────────►│     Next.js Dashboard (UI)       │
  │   (Webhook Ingest)  │          │   Real-time agent thought stream │
  └─────────────────────┘          └──────────────────────────────────┘
         │                                        ▲
         │ 2. Push Job + 202 Accepted             │
         ▼                                        │ 7. SSE Stream
  ┌─────────────────────┐                         │
  │   Redis Task Queue  │                         │
  └─────────────────────┘                         │
         │                                        │
         │ 3. Worker pulls job                    │
         ▼                                        │
  ┌─────────────────────────────────────────────────────────┐
  │                  Python Worker (ARQ)                    │
  │                                                         │
  │   ┌─────────────────────────────────────────────────┐   │
  │   │           LangGraph Agent Loop                  │   │
  │   │                                                 │   │
  │   │  [INVESTIGATE] → [HYPOTHESIZE] → [WRITE FIX]  │   │
  │   │       ▲               │              │          │   │
  │   │       │               ▼              ▼          │   │
  │   │       └──────── [RUN TESTS] ←── [SANDBOX]      │   │
  │   │                      │                          │   │
  │   │                      ▼ (pass)                   │   │
  │   │               [CREATE PR]                       │   │
  │   └─────────────────────────────────────────────────┘   │
  └─────────────────────────────────────────────────────────┘
         │                    │
         │                    │ 4. Semantic search + save state
         ▼                    ▼
  ┌────────────────────────────────┐     ┌──────────────────┐
  │     PostgreSQL (Neon)          │     │  Groq / Gemini   │
  │  ┌──────────┐  ┌────────────┐ │     │  (LLM Reasoning) │
  │  │  Events  │  │  pgvector  │ │     └──────────────────┘
  │  │  PRs     │  │ Codebase   │ │
  │  │  Logs    │  │ Embeddings │ │
  │  └──────────┘  └────────────┘ │
  └────────────────────────────────┘
```

### The Agent Loop (LangGraph State Machine)

```
                    ┌──────────────────┐
      Webhook ──►   │   INGEST ERROR   │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  VECTOR SEARCH   │  ◄── pgvector similarity search
                    │ (Find broken fn) │       over entire codebase
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  LLM REASONING   │  ◄── Groq Llama 3.3 70B
                    │ (Form hypothesis)│       or Gemini Flash
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   WRITE PATCH    │  ◄── Code generation
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  SANDBOX TESTS   │  ◄── Docker container
                    │ (Run test suite) │       (isolated, no network)
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │ FAIL         │              │ PASS
              │              │              │
     ┌────────▼────┐         │    ┌─────────▼──────────┐
     │  REFLECT &  │         │    │   VALIDATE SUITE   │  ◄── Full test suite
     │  RETRY (n)  │         │    │  (All modules pass) │       (not just local)
     └────────┬────┘         │    └─────────┬──────────┘
              │              │              │
              └──────────────┘    ┌─────────▼──────────┐
                                  │    CREATE PR        │  ◄── GitHub App API
                                  │  + Notify Slack     │
                                  └────────────────────┘
```

---

## 🛠️ Technology Stack

### Backend & Orchestration

| Technology | Role | Why This Choice |
|-----------|------|-----------------|
| **Python 3.12** | Primary language | Native home of the ML/AI ecosystem |
| **FastAPI** | API Gateway & Webhook Ingest | Async I/O (`asyncio`)  doesn't block while LLMs think |
| **LangGraph** | AI Agent Orchestration | Cyclic state machines for reflect-and-retry loops. Standard LangChain is linear; bugs aren't. |
| **ARQ** | Background Task Worker | Async-native (built on `asyncio`), lightweight, perfect for our FastAPI stack |
| **GitHub App (PyGithub)** | PR Creation & Repo Access | Fine-grained permissions per repo without OAuth token sprawl |

### Data Layer

| Technology | Role | Why This Choice |
|-----------|------|-----------------|
| **PostgreSQL (Neon)** | Primary Database | ACID compliance for audit trails. Every action the AI takes is logged. |
| **pgvector** | Vector Similarity Search | Extends PostgreSQL with `<=>` cosine distance operator. No extra infra  vectors live alongside relational data. |
| **Redis** | Task Queue | Decouples HTTP requests from 45-second AI jobs. FastAPI returns `202 Accepted` instantly. |

### AI & LLM

| Technology | Role | Why This Choice |
|-----------|------|-----------------|
| **Groq API (Llama 3.3 70B)** | Primary LLM | LPU hardware delivers ~750 tokens/sec  critical for fast agent loops |
| **Google Gemini Flash** | Fallback / Large context | 1M token context window for huge codebases |
| **OpenAI `text-embedding-3-small`** | Embedding Generation | State-of-the-art code embeddings for vector search accuracy |
| **LangSmith** | Agent Observability | Trace every reasoning step, token usage, and retry loop for debugging |

### Execution & Security

| Technology | Role | Why This Choice |
|-----------|------|-----------------|
| **Docker (sandboxed containers)** | Test Execution | AI-generated code runs in isolated containers with no network access and memory caps  never on the host |

### Frontend

| Technology | Role | Why This Choice |
|-----------|------|-----------------|
| **Next.js 15** | Dashboard | App Router, React Server Components, built-in API routes |
| **Tailwind CSS** | Styling | Rapid UI development, consistent design tokens |
| **Server-Sent Events (SSE)** | Real-time Agent Stream | Unidirectional stream of agent "thoughts" to the UI  simpler than WebSockets for this use case |

---

## 📊 Data Flow: Step by Step

Let's trace a real bug: `ZeroDivisionError` in `billing.py`

```
Step 1  INGESTION
  ├── Sentry detects crash, sends JSON webhook to /api/v1/ingest
  ├── FastAPI validates payload with Pydantic
  ├── Saves Event record to PostgreSQL  [status: PENDING]
  ├── Drops job into Redis queue
  └── Returns HTTP 202 Accepted to Sentry  ←  instant, no blocking

Step 2  WORKER WAKEUP
  ├── ARQ worker sees new job in Redis
  └── Instantiates the LangGraph agent with the error context

Step 3  VECTOR SEARCH
  ├── Error message → embedding vector (1536 dimensions)
  ├── pgvector query: SELECT chunk, file_path
  │     ORDER BY embedding <=> $1  LIMIT 10
  └── Returns: ["billing.py:L135-160", "payment_utils.py:L42-80"]

Step 4  AGENT REASONING LOOP
  Iteration 1:
  ├── LLM reads the top 3 code chunks
  ├── Identifies: `total / discount` with no zero-check on line 142
  ├── Writes patch: adds `if discount == 0: raise ValueError(...)`
  ├── Generates unit test
  ├── Runs test in Docker container
  └── Result: ❌ FAIL  test asserts wrong exception type

  Iteration 2:
  ├── LLM reads failure output
  ├── Revises patch and test
  ├── Runs test in Docker container
  └── Result: ✅ PASS

  Full Suite Validation:
  └── Runs ALL project tests in sandbox → ✅ 47/47 pass

Step 5  COMPLETION
  ├── Updates PostgreSQL record  [status: COMPLETED]
  ├── Calls GitHub App API → Opens Pull Request #847
  ├── Posts Slack notification with PR link
  └── SSE stream pushes final state to Next.js dashboard
```

---

## 🗺️ Build Roadmap

We build strictly left to right  **no AI until the infrastructure is solid.**

```
  Phase 1          Phase 2          Phase 3          Phase 4          Phase 5
  ─────────        ─────────        ─────────        ─────────        ─────────
  The Desk &       The Rail         The Memory       The Chef         The Waiter
  The Pantry

  FastAPI    ──►   Redis      ──►   pgvector   ──►   LangGraph  ──►   Next.js
  PostgreSQL       ARQ Worker       Indexer          Agent            Dashboard
  Webhooks         Task Queue       Embeddings       Groq/Gemini      SSE Stream
                                    Chunker          GitHub PR        Real-time UI
```

### Phase 1  The Foundation *(Infrastructure Only, No AI)*
- [ ] FastAPI project scaffold with Pydantic settings
- [ ] PostgreSQL schema: `events`, `pull_requests`, `agent_logs`
- [ ] `POST /api/v1/ingest`  receives webhook, validates, saves to DB
- [ ] `GET /api/v1/events`  lists all ingested errors
- [ ] Alembic migrations
- [ ] Docker Compose for local dev (FastAPI + Postgres)

### Phase 2  Async Queue *(No AI yet)*
- [ ] Redis service added to Docker Compose
- [ ] ARQ worker setup with job definitions
- [ ] FastAPI enqueues job and returns `202 Accepted` immediately
- [ ] Worker picks up job, updates event status to `PROCESSING`
- [ ] End-to-end test: Webhook → Queue → Worker → DB status update

### Phase 3  Codebase Memory
- [ ] `indexer/` service: clones repo, chunks by function/class boundaries
- [ ] Embedding pipeline: OpenAI `text-embedding-3-small`
- [ ] pgvector schema: `code_chunks` table with `VECTOR(1536)` column
- [ ] Vector search endpoint: `POST /api/v1/search`
- [ ] GitHub push webhook → triggers re-indexing on new commits

### Phase 4  The AI Agent
- [ ] LangGraph state machine with nodes: `investigate`, `hypothesize`, `patch`, `test`, `validate`, `submit`
- [ ] Docker sandbox service for isolated test execution
- [ ] Retry loop: max 5 iterations before escalating to human
- [ ] GitHub App integration for PR creation
- [ ] LangSmith tracing on all agent runs
- [ ] Full agent integration test with a dummy buggy repo

### Phase 5  The Dashboard
- [ ] Next.js app with App Router
- [ ] SSE endpoint in FastAPI: `GET /api/v1/events/{id}/stream`
- [ ] Incident list page with status badges
- [ ] Live agent trace viewer (watch the agent think, step by step)
- [ ] PR approval / dismiss controls
- [ ] Slack webhook notification on completion

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose
- A [Groq API Key](https://console.groq.com) (free tier available)
- A [Neon](https://neon.tech) or Supabase PostgreSQL instance
- A [GitHub App](https://github.com/settings/apps/new) with `Contents: Read & Write` and `Pull Requests: Write` permissions

### Local Development Setup

**1. Clone the repository**
```bash
git clone https://github.com/abdullahxdev/nerve.git
cd nerve
```

**2. Set up environment variables**
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/nerve

# Redis
REDIS_URL=redis://localhost:6379

# LLM
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=...
OPENAI_API_KEY=sk-...   # for embeddings

# GitHub App
GITHUB_APP_ID=...
GITHUB_APP_PRIVATE_KEY_PATH=./github-app.pem
GITHUB_WEBHOOK_SECRET=...

# Observability
LANGCHAIN_API_KEY=...   # LangSmith
LANGCHAIN_TRACING_V2=true
```

**3. Start infrastructure services**
```bash
docker compose up -d postgres redis
```

**4. Install Python dependencies**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**5. Run database migrations**
```bash
alembic upgrade head
```

**6. Start the FastAPI backend**
```bash
uvicorn app.main:app --reload --port 8000
```

**7. Start the ARQ worker**
```bash
arq app.worker.WorkerSettings
```

**8. Start the Next.js frontend**
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000` for the dashboard and `http://localhost:8000/docs` for the API.

---

## 📁 Project Structure

```
nerve/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── ingest.py        # Webhook ingestion routes
│   │   │       ├── events.py        # Event listing & detail routes
│   │   │       └── stream.py        # SSE streaming endpoint
│   │   ├── agent/
│   │   │   ├── graph.py             # LangGraph state machine definition
│   │   │   ├── nodes/
│   │   │   │   ├── investigate.py   # Vector search node
│   │   │   │   ├── patch.py         # Code generation node
│   │   │   │   ├── test.py          # Sandbox test execution node
│   │   │   │   └── submit.py        # GitHub PR creation node
│   │   │   └── state.py             # AgentState TypedDict
│   │   ├── db/
│   │   │   ├── models.py            # SQLAlchemy models
│   │   │   └── session.py           # Async DB session
│   │   ├── indexer/
│   │   │   ├── chunker.py           # Code chunking by function boundary
│   │   │   └── embedder.py          # Embedding generation + pgvector upsert
│   │   ├── worker.py                # ARQ worker settings & job definitions
│   │   └── main.py                  # FastAPI application entry point
│   ├── alembic/                     # Database migrations
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx                 # Incident dashboard
│   │   ├── incidents/[id]/page.tsx  # Live agent trace viewer
│   │   └── layout.tsx
│   ├── components/
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🔌 API Reference

### Ingest an Error Event

```http
POST /api/v1/ingest
Content-Type: application/json
X-Nerve-Signature: sha256=...

{
  "source": "sentry",
  "error_type": "ZeroDivisionError",
  "message": "division by zero",
  "stack_trace": "File billing.py, line 142...",
  "repository": "org/repo",
  "environment": "production",
  "metadata": {}
}
```

**Response:**
```json
{
  "event_id": "evt_01J2X...",
  "status": "queued",
  "stream_url": "/api/v1/events/evt_01J2X.../stream"
}
```

### Stream Agent Progress (SSE)

```http
GET /api/v1/events/{event_id}/stream
Accept: text/event-stream
```

**Events emitted:**
```
event: agent_step
data: {"node": "investigate", "message": "Searching codebase for ZeroDivisionError context...", "timestamp": "..."}

event: agent_step
data: {"node": "patch", "message": "Writing fix for billing.py:142...", "timestamp": "..."}

event: complete
data: {"pr_url": "https://github.com/org/repo/pull/847", "iterations": 2}
```

---

## 🛡️ Security Considerations

> **Important:** Running AI-generated code requires serious isolation. We never execute AI output on the host system.

- **Sandboxed Execution**: All AI-generated code and tests run inside Docker containers with:
  - No network access (`--network none`)
  - Memory capped at 512MB (`--memory 512m`)
  - CPU limited (`--cpus 0.5`)
  - Read-only filesystem (except `/tmp`)
  - Auto-removed after execution (`--rm`)
- **Webhook Verification**: All incoming webhooks are verified via HMAC-SHA256 signature
- **GitHub App (not OAuth)**: Fine-grained repo permissions, no user token required
- **Audit Trail**: Every agent action, LLM call, and code execution is logged to PostgreSQL with timestamps

---

## 🤝 Contributing

Contributions are what make open source great. Any contribution you make is **greatly appreciated**.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages.

---

## 📄 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for more information.

---

<div align="center">

Built with obsession by **[@abdullahxdev](https://github.com/abdullahxdev)**

*"The best on-call engineer is the one that's already awake."*

⭐ **Star this repo if you find it interesting**

</div>
