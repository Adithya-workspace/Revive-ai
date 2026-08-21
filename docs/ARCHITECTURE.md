# REVIVE AI — Architecture

**Autonomous Revenue Recovery Intelligence**
Track 03 — AI Revenue Recovery | Razorpay AI Buildathon

---

## 1. System Overview

REVIVE AI is a bounded, auditable agent system that finds revenue slipping away (failed payments, abandoned checkouts, overdue invoices), figures out why, decides on a recovery action from a fixed set of allowed actions, gets that action authorized by a deterministic policy engine, executes it (real test-mode API or clearly-labeled simulation), verifies the actual outcome, and records everything.

The system is deliberately **not** "an LLM that gives advice." The LLM is one participant in a pipeline where a non-negotiable, non-LLM policy layer sits between every AI suggestion and every action that touches money or a customer.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND — Next.js 14 (App Router) + TypeScript + Tailwind  │
│  Dashboard, Case pages, Analytics, Audit, Policies, Demo Mode │
└───────────────────────────┬────────────────────────────────┘
                            │ REST/JSON (fetch)
┌───────────────────────────▼────────────────────────────────┐
│  BACKEND API — FastAPI (Python)                              │
│  Auth, request validation, orchestrates everything below     │
└───────────────────────────┬────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐  ┌─────────────────┐  ┌──────────────────┐
│ DETECTION      │  │ AGENT GRAPH      │  │ EVALUATION ENGINE │
│ (deterministic │  │ (LangGraph)      │  │ (standalone       │
│  SQL/rules)    │  │ see Section 4    │  │  script, Phase 17)│
└───────┬────────┘  └────────┬─────────┘  └─────────┬────────┘
        │                    │                       │
        └────────────────────┼───────────────────────┘
                             ▼
                 ┌───────────────────────┐
                 │  PostgreSQL (Neon)     │
                 │  see Section 6 schema  │
                 └───────────┬───────────┘
                             │
                 ┌───────────▼───────────┐
                 │  Razorpay TEST API     │
                 │  or Simulation Layer   │
                 │  (Section 5)           │
                 └────────────────────────┘
```

Two things worth stating explicitly because they're easy to get wrong under time pressure:

- **The Agent Graph never talks to the database directly for writes that matter.** It returns structured results; the API layer is what persists them. This keeps the LangGraph code testable in isolation (you can unit-test a node with a fake state object, no DB needed).
- **Detection is not a graph node.** It's a plain scheduled/on-demand query job that creates `revenue_risk_cases` rows. Only once a case exists does it enter the agent graph. This mirrors how a real system would work — detection runs continuously and cheaply, diagnosis/strategy only run on things worth spending LLM calls on.

---

## 3. Why FastAPI + Next.js (not a single Node stack)

You've built Nexus OS and HireFlow AI in Next.js/Node before, so this is a deliberate deviation — here's the reasoning, since you should be able to defend every stack choice to a judge:

- **LangGraph is Python-native.** Running it from Node would mean either a JS reimplementation (losing LangGraph's tooling) or shelling out to a Python subprocess per request (fragile, hard to test, hard to debug).
- **One language for all "trust-critical" code.** Detection, policy engine, action executor, verification, and evaluation script all live in Python. That means the same Pydantic models validate data at every stage — no risk of a field silently meaning something different in a JS type vs a Python type.
- **The evaluation engine is a real command-line deliverable** (`python evaluation/run_evaluation.py`, Section 46 of your spec). That's naturally a Python script; keeping it in the same codebase as the agent logic (not a separate reimplementation) guarantees the evaluation is testing the *actual* production logic, not a parallel copy that could drift.
- **Next.js stays the frontend** because that's genuinely the best tool for the dashboard, and you already have real muscle memory there from Nexus OS.

The trade-off: you're maintaining two runtimes (Node + Python) instead of one. That's a real cost. I'm judging it worth it here because the alternative — agent logic in Node — would fight the framework the whole way.

---

## 4. Agent State Machine (LangGraph)

### 4.1 The State Object

Every case that enters the graph carries a single typed state object through every node:

```python
class RecoveryCaseState(TypedDict):
    case_id: str
    customer_id: str
    scenario: Literal["failed_payment", "checkout_abandonment", "overdue_receivable"]
    amount_at_risk: float
    event_data: dict          # raw source record snapshot (transaction/checkout/invoice)
    customer_history: dict    # precomputed rollup: past successes/failures/etc

    diagnosis: str | None
    diagnosis_confidence: float | None
    diagnosis_evidence: list[str]

    recovery_probability: float | None
    recovery_score_source: Literal["rules", "statistical", "ml"] | None

    recommended_action: str | None       # must be a value from the Action enum
    strategy_confidence: float | None
    strategy_source: Literal["rules", "llm"] | None

    policy_decision: Literal["APPROVED", "REJECTED", "NEEDS_HUMAN"] | None
    policy_reason: str | None

    action_result: dict | None           # action_id, status, mode (REAL/TEST/SIMULATED), etc
    verification_result: dict | None
    recovered_amount: float | None

    escalation_status: str | None
    stop_reason: str | None

    audit_events: list[dict]             # appended to at every node, persisted at the end
```

### 4.2 Node-by-Node Responsibility

| Node | Input | Output | LLM involved? |
|---|---|---|---|
| `diagnose_node` | event_data, customer_history | diagnosis, confidence, evidence | Rules first; LLM only for the ambiguous residual bucket |
| `score_node` | diagnosis, customer_history | recovery_probability, source label | No — rules/statistical baseline (Section 9 of your spec) |
| `strategy_node` | diagnosis, score | recommended_action (from fixed enum), confidence | Yes, with strict output validation |
| `policy_node` | recommended_action, amount, confidence, case history | policy_decision, reason | **Never** — pure deterministic function |
| `action_node` | approved action | action_result | No |
| `verification_node` | action_result | verification_result, recovered_amount | No — reads real payment/invoice status |
| `measurement_node` | verification_result | updates aggregate metrics | No |
| `escalation_node` | policy_decision = REJECTED/NEEDS_HUMAN | escalation record | No |

Every node appends to `audit_events` before returning — this is what makes the audit trail complete rather than reconstructed after the fact.

### 4.3 Graph Edges (Control Flow)

```
diagnose_node → score_node → strategy_node → policy_node
                                                  │
                        ┌─────────────────────────┼───────────────────────┐
                        ▼                          ▼                        ▼
                 action_node              escalation_node            escalation_node
                        │                  (REJECTED)                (NEEDS_HUMAN)
                        ▼
              verification_node
                        │
                        ▼
              measurement_node
                        │
                        ▼
                 (check stop rules)
                    │         │
              STOP  │         │  case_age/retry-eligible
                    ▼         ▼
                  END     back to score_node
                          (next attempt cycle,
                           only if policy allows another attempt)
```

The loop-back edge is the one place infinite-retry risk lives — it is only reachable if `policy_node` explicitly approves another attempt, and the policy node itself enforces a hard max-attempts cap independent of anything the LLM says.

---

## 5. Action Execution Modes

Every `action_result` record carries an explicit `mode` field:

| Mode | Meaning |
|---|---|
| `REAL` | Actual Razorpay production call — **not used in this competition build** |
| `TEST` | Real call to Razorpay's test-mode API — a real HTTP round trip, fake money |
| `SIMULATED` | No external call at all — internal logic mimics an outcome (used where Razorpay test mode doesn't support the exact operation, e.g. "customer opens reminder email") |

The dashboard renders a colored badge for this on every case and action row. This directly satisfies Section 12/44/45 of your spec — nothing is allowed to look more "real" than it is.

---

## 6. Data Model (summary — full DDL comes in Phase 3)

```
merchants ──< customers ──< transactions ──< payments
                   │
                   ├──< checkout_sessions
                   ├──< invoices ──< promises_to_pay
                   └──< subscriptions

revenue_risk_cases (hub table)
   source_type + source_id  →  points at transaction / checkout_session / invoice
   │
   ├──< diagnoses
   ├──< recovery_scores
   ├──< recovery_actions ──< action_results
   ├──< escalations
   └──< audit_events (append-only, never updated/deleted)

policies (versioned config table, not hardcoded constants)
```

The `revenue_risk_cases` table is the spine of the whole system — nearly every dashboard screen and every agent node reads or writes through it.

---

## 7. Non-Negotiable Safety Rules (repeated here because they drive the architecture)

1. Policy engine code contains **no LLM calls, no LLM-derived thresholds evaluated at runtime**. Config values it reads come from the `policies` table, editable only by an admin action, never by the agent.
2. All LLM outputs that feed a financial action are validated against a Pydantic schema before touching the policy engine. Invalid output → rejected, logged, never partially trusted.
3. A case is `recovered` only when `verification_node` confirms it against real payment/invoice status — never set earlier in the pipeline.
4. Every action carries an idempotency key of `(case_id, action_type, attempt_number)` — replaying the same request is a no-op, not a duplicate.
5. Every node writes to `audit_events` — the trail is built during execution, not reconstructed afterward.

---

## 8. Proposed Project Structure

```
revive-ai/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entrypoint
│   │   ├── api/                    # route handlers (cases, actions, analytics, audit...)
│   │   ├── agents/                 # LangGraph graph + node functions
│   │   ├── detection/              # deterministic risk-detection queries
│   │   ├── policies/               # the policy engine — kept isolated on purpose
│   │   ├── actions/                # action executor + Razorpay client + simulation layer
│   │   ├── models/                 # SQLAlchemy models
│   │   ├── schemas/                # Pydantic request/response + LLM-output schemas
│   │   └── services/               # shared business logic (scoring, verification, etc)
│   ├── database/
│   │   └── migrations/             # Alembic migrations
│   ├── evaluation/
│   │   └── run_evaluation.py       # Phase 17 deliverable
│   ├── scripts/
│   │   └── generate_synthetic_data.py
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
│
├── frontend/
│   ├── app/                        # Next.js App Router pages
│   ├── components/
│   ├── lib/                        # API client, types
│   └── package.json
│
└── docs/
    ├── ARCHITECTURE.md             # this file
    ├── API.md
    ├── EVALUATION.md
    ├── DEMO.md
    ├── SECURITY.md
    └── LIMITATIONS.md
```

**Purpose of each top-level directory:**
- `backend/app/agents` — the LangGraph graph lives here in isolation, so it can be imported and unit-tested by both the API and the evaluation script without duplication.
- `backend/app/policies` — deliberately its own module, not folded into `agents`, to make it visually obvious in code review that this is the non-LLM safety boundary.
- `backend/evaluation` — a standalone script, not a route — judges should be able to run it from the command line with zero frontend involvement.
- `docs/` — the six required documents live together, separate from code.

---

## 9. What We're Explicitly Deferring

- Background/async job queue (Celery, etc.) — not needed at this scale; FastAPI's built-in background tasks are enough for a competition build.
- Multi-region/production deployment concerns — out of scope; this is a test-mode demo.
- ML-based recovery scoring — starts as rules/statistical baseline (Section 9); only upgraded to real ML if time remains (P2).
