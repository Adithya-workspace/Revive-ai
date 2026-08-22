# REVIVE AI

**Autonomous Revenue Recovery Intelligence**
Built for the Razorpay AI Buildathon — Track 03: AI Revenue Recovery

---

## What this is

REVIVE AI detects revenue that's slipping away — failed payments, abandoned checkouts, overdue B2B invoices — diagnoses why, decides on a bounded recovery action, gets that action authorized by a deterministic policy engine, executes it, verifies the real outcome, and records everything in an immutable audit trail.

This is not an LLM that gives merchants advice. It's a controlled agent system where a non-negotiable, non-LLM policy layer sits between every AI suggestion and every action that touches money or a customer.

> **Status:** Actively in development. This README reflects what's actually built and verified — nothing here is aspirational or fabricated. See [Progress](#progress) below.

---

## Architecture

Full architecture, agent workflow, and data model are documented in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

Frontend (Next.js) → Backend API (FastAPI) → Detection Layer (deterministic)
↓
Agent Graph (LangGraph)
diagnose → score → strategy → policy → act → verify
↓
PostgreSQL (Neon) + Audit Trail


**Tech stack:** FastAPI + SQLAlchemy + Alembic (backend), Next.js + TypeScript + Tailwind (frontend), PostgreSQL on Neon, LangGraph for agent orchestration, Llama 3.3/gpt-oss-120b via Groq for LLM reasoning (diagnosis, messaging) — with a hard rule that the policy engine never involves an LLM call.

---

## Progress

- [x] **Phase 1** — Project structure, architecture docs
- [x] **Phase 2** — FastAPI + Next.js scaffolded and running
- [x] **Phase 3** — Database schema (`merchants`, `customers`, `transactions`, `checkout_sessions`, `invoices`, `revenue_risk_cases`) migrated to Neon via Alembic
- [x] **Phase 4** — Synthetic data generator: 870 customers across 6 behavioral archetypes, 10,600+ reproducible revenue events (seed=42)
- [x] **Phase 5** — Deterministic revenue detection layer: 2,529 revenue-risk cases detected across all three MVP scenarios, idempotent and re-runnable
- [x] **Phase 6** — Recovery scoring: 2,529 cases scored using a transparent, factor-based model (scenario baseline, customer history, retry count, case age, amount) — average recovery probability 0.503, explicitly labeled as rules-based (not ML)
- [x] **Phase 7** — Hybrid diagnosis: 1,808 of 2,529 cases diagnosed (1,628 resolved deterministically via rules, 180 via LLM reasoning for ambiguous checkout-abandonment cases using Llama 3.3/gpt-oss-120b via Groq). Remaining 721 cases queued for a future run before final evaluation — idempotent, safe to resume anytime.
- [ ] **Phase 8** — Recovery strategy agent
- [ ] **Phase 9** — Policy / guardrail engine
- [ ] **Phase 10** — Action execution layer
- [ ] **Phase 11** — Verification
- [ ] **Phase 12** — Audit trail
- [ ] **Phase 13** — Analytics
- [ ] **Phase 14** — Frontend dashboard
- [ ] **Phase 15** — Razorpay test-mode integration
- [ ] **Phase 16** — Testing
- [ ] **Phase 17** — Evaluation engine + baseline comparison
- [ ] **Phase 18** — Demo mode
- [ ] **Phase 19** — Polish
- [ ] **Phase 20** — Final documentation

---

## Running this locally

### Prerequisites
- Python 3.11+
- Node.js 18+
- A PostgreSQL database (this project uses [Neon](https://neon.tech))

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your own `DATABASE_URL`:

```bash
cp .env.example .env
```

Run migrations:

```bash
alembic upgrade head
```

Generate the synthetic dataset:

```bash
python -m scripts.generate_synthetic_data
```

Run a revenue detection scan:

```bash
python -m scripts.run_detection
```

Start the API server:

```bash
uvicorn app.main:app --reload --port 8080
```

API docs available at `http://localhost:8080/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Runs at `http://localhost:3000`.

---

## Project structure

revive-ai/
├── backend/
│ ├── app/
│ │ ├── main.py # FastAPI entrypoint
│ │ ├── api/ # route handlers
│ │ ├── detection/ # deterministic risk detection rules
│ │ ├── agents/ # LangGraph agent graph (Phase 7+)
│ │ ├── policies/ # policy/guardrail engine (Phase 9+)
│ │ ├── actions/ # action executor (Phase 10+)
│ │ ├── models/ # SQLAlchemy models
│ │ └── database.py # DB connection/session management
│ ├── database/migrations/ # Alembic migrations
│ ├── scripts/ # CLI utilities (data gen, detection, etc.)
│ └── evaluation/ # batch evaluation engine (Phase 17)
├── frontend/ # Next.js dashboard
└── docs/
├── ARCHITECTURE.md
└── REVIVE_AI_Phase0_Planning.md


---

## Key design principles

1. **AI proposes, policy disposes.** Every action an LLM suggests passes through a deterministic policy engine with zero LLM involvement before it's allowed to execute.
2. **Nothing is claimed recovered until verified.** A case is only marked `recovered` after the verification layer confirms it against real payment/invoice status — never earlier in the pipeline.
3. **Every action is idempotent.** Retrying the same action never duplicates it.
4. **REAL vs TEST vs SIMULATED is always labeled.** No output is ever allowed to look more "real" than it actually is.
5. **No fabricated metrics.** Every number in the final dashboard and evaluation report is traceable to an actual run against the synthetic dataset.

---

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — full system architecture, agent state machine, data model
- [`docs/REVIVE_AI_Phase0_Planning.md`](docs/REVIVE_AI_Phase0_Planning.md) — original requirements analysis and roadmap

Additional docs (`API.md`, `EVALUATION.md`, `DEMO.md`, `SECURITY.md`, `LIMITATIONS.md`) will be added as their corresponding phases are completed.

---

## Author

Built by Adithya, B.Sc. Computer Science student, for the Razorpay AI Buildathon.
