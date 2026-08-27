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
- [x] **Phase 7** — Hybrid diagnosis: all 2,529 cases diagnosed (rules + LLM via Llama 3.3/gpt-oss-120b through Groq for ambiguous cases). No backlog remaining.
- [x] **Phase 8** — Recovery strategy agent: 1,808 cases strategized using deterministic override rules on top of diagnosis (low-confidence → escalate, low-probability → stop, high-value → escalate). Total expected recoverable value: ₹1,02,32,059.80. No LLM calls in this stage.
- [x] **Phase 9** — Policy / guardrail engine: 1,808 proposed actions evaluated against three versioned, database-backed policies (max 2 automatic retries, ₹5,000 automatic-action ceiling, 0.60 minimum confidence). Result: 784 approved, 726 routed to human, 298 rejected outright (retry cap violations). Zero LLM involvement — this is the pure deterministic authorization boundary between AI suggestions and real actions.
- [x] **Phase 10** — Action execution layer: 677 policy-approved actions executed in SIMULATED mode (immediate-outcome retries grounded in actual recovery_probability: 158 success, 125 failed; message-based actions: 394 pending verification). Real Razorpay test-mode integration intentionally deferred to Phase 15.
- [x] **Phase 11** — Verification: 677 action results verified against real source-record updates (transactions) or probability-grounded simulated customer response (reminders). 368 cases confirmed genuinely recovered — verification is the ONLY component permitted to mark a case "recovered," enforcing Section 13's no-fabricated-recovery rule.
- [x] **Phase 12** — Audit trail: schema and backfill logic built (CASE_DETECTED → RECOVERY_SCORE_CALCULATED → DIAGNOSIS_COMPLETED → STRATEGY_SELECTED → POLICY_DECISION → ACTION_EXECUTED → VERIFICATION_COMPLETED → CASE_RECOVERED), with a timestamp-ordering fix applied. Backfill run itself deferred — table is currently empty and needs `python -m scripts.backfill_audit_trail` before demo/evaluation.
- [x] **Phase 13** — Analytics: real aggregate metrics computed directly from pipeline data — ₹3,05,81,527.55 total revenue at risk, ₹6,85,688.07 verified recovered (6.7% recovery rate on the currently-processed subset; rate will rise once the remaining 721-case diagnosis backlog clears), plus by-scenario and policy-decision breakdowns. No fabricated numbers — every figure traces to an actual query.
- [x] **Phase 14** — Frontend dashboard complete: all nine screens built and verified against live data — Dashboard, Revenue at Risk, Case Detail (with human approve/reject), Recovery Cases, Escalations, Customers, Actions, Analytics (charts), Audit Trail (12,189 events), and Settings (live policy visibility). Design system: dark instrument-panel aesthetic with functional status-color system and "recovery pulse" signature motif.
- [ ] **Phase 15** — Razorpay test-mode integration
- [x] **Phase 16** — Testing: 37 automated tests passing (pytest, isolated `revive_test` database with per-test transaction rollback) — detection (all 3 scenarios + idempotency), policy engine (retry cap, amount ceiling, confidence floor, live-value verification), scoring, strategy, duplicate-action protection, and two required end-to-end pipeline tests (successful recovery path and safe-failure/escalation path).
- [x] **Phase 17** — Evaluation engine + baseline comparison: full dataset (2,529 cases, zero backlog) evaluated against a naive baseline. REVIVE recovered ₹8,92,167.88 with a 52.7% per-attempt recovery rate — outperforming the naive baseline's 47.4% by +5.3pp — while avoiding 1,270 unnecessary automatic interventions through policy gating.
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

```
revive-ai/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entrypoint
│   │   ├── api/                 # route handlers
│   │   ├── detection/           # deterministic risk detection rules
│   │   ├── agents/              # LangGraph agent graph (Phase 7+)
│   │   ├── policies/            # policy/guardrail engine (Phase 9+)
│   │   ├── actions/              # action executor (Phase 10+)
│   │   ├── models/                # SQLAlchemy models
│   │   └── database.py            # DB connection/session management
│   ├── database/migrations/       # Alembic migrations
│   ├── scripts/                   # CLI utilities (data gen, detection, etc.)
│   └── evaluation/                # batch evaluation engine (Phase 17)
├── frontend/                      # Next.js dashboard
└── docs/
    ├── ARCHITECTURE.md
    └── REVIVE_AI_Phase0_Planning.md
```

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
