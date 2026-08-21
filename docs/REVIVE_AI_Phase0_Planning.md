# REVIVE AI — Phase 0: Requirements Analysis & Planning

**Track 03 — AI Revenue Recovery | Razorpay AI Buildathon**

---

## 1. Requirements Checklist

### Must demonstrate (non-negotiable, per problem statement)
- [ ] DETECT revenue at risk (failed payments, checkout abandonment, overdue receivables)
- [ ] DIAGNOSE root cause
- [ ] DECIDE recovery strategy from a bounded action set
- [ ] Deterministic POLICY engine approves/rejects every action (AI never has unilateral authority)
- [ ] ACT — execute or clearly-labeled simulate
- [ ] VERIFY the action actually worked before claiming recovery
- [ ] MEASURE recovered money across a batch (not a single anecdote)
- [ ] STOP rules (max retries, opt-out, low probability, etc.)
- [ ] ESCALATE to human when policy/confidence demands it
- [ ] Immutable AUDIT TRAIL for every event
- [ ] No fabricated numbers — every metric traceable to an actual run

### Implicit requirements (judges will probe these)
- Idempotency (no duplicate charges/actions on retry)
- Graceful handling of a simulated external API failure
- Clear LIVE / TEST / SIMULATED labeling everywhere
- Baseline comparison (naive strategy vs REVIVE) using real numbers
- Reproducible evaluation (fixed seed, versioned policy/model)
- A dashboard that reads like a fintech ops tool, not a chatbot demo

---

## 2. MVP Definition

The MVP is the **three core scenarios fully working end-to-end**, not partially:

1. **Failed Payment Recovery** — retry/reminder logic based on failure reason + history
2. **Checkout Abandonment Recovery** — nudge messages based on inactivity + context
3. **Overdue Receivables (B2B)** — collection sequence + promise-to-pay tracking

Each must go all the way through: Detect → Diagnose → Score → Decide → Policy → Act (real/simulated) → Verify → Measure → Audit. A single scenario done completely, with real batch metrics, beats three scenarios done shallowly.

Everything else (Hinglish, voice, mandate sequencer, ML scoring model) is explicitly **P2/P3** — do not touch until MVP is demo-ready.

---

## 3. Strongest Differentiators

What will separate this from "yet another LLM wrapper" submission:

1. **Visible AI/deterministic split** — the UI literally labels each number/decision as "Rule-based," "ML," or "LLM reasoning." Judges rarely see this discipline.
2. **Policy engine as a first-class, inspectable component** — a dedicated Policies page showing the exact limits, and every case detail page showing "AI proposed X → Policy approved/rejected because Y."
3. **A real stop/escalate demo** — most hackathon bots retry forever. Showing REVIVE *refuse* to act is more convincing than showing it act.
4. **Baseline vs REVIVE on the same 10k-event dataset** — a real lift number (e.g. "+14.2pp recovery rate") is far more credible than a demo video.
5. **Idempotency proof** — deliberately fire the same action twice in the demo and show it's a no-op the second time.

---

## 4. Proposed Product Architecture

```
Frontend (Next.js dashboard)
        │  REST/JSON
        ▼
Backend API (FastAPI)
        │
        ▼
Revenue Event Ingestion  ──►  PostgreSQL (transactions, invoices, checkout_sessions...)
        │
        ▼
Detection Layer (deterministic rules over the DB)
        │
        ▼
Agent State Machine (LangGraph)
  ┌─────────────────────────────────────────────┐
  │ Diagnosis Node → Scoring Node → Strategy Node │
  │        → Policy Node → Action Node            │
  │        → Verification Node → Measurement Node │
  └─────────────────────────────────────────────┘
        │
        ▼
Action Layer: Razorpay TEST mode  |  Simulation layer (clearly labeled)
        │
        ▼
Audit Log (append-only table) + Analytics/Evaluation engine
        │
        ▼
Frontend reads everything back via API
```

This matches your Section 50 diagram closely — I've just made explicit that the "Agent State Machine" is one LangGraph graph with multiple nodes, not eight separate services. That's a deliberate simplification for a 2nd-year timeline; I'll flag it to judges as an intentional architecture choice, not a shortcut.

---

## 5. Agent Workflow (LangGraph State Machine)

One graph, one `RecoveryCaseState` object flowing through nodes:

```
detect_case (usually pre-computed by the deterministic detector, not a graph node)
   → diagnose_node        (rules + optional LLM reasoning, structured output)
   → score_node            (deterministic/statistical recovery probability)
   → strategy_node          (LLM or rules picks ONE action from a fixed enum)
   → policy_node             (pure deterministic code — no LLM here, ever)
      ├─ APPROVED → action_node → verification_node → measurement_node
      ├─ REJECTED → escalation_node
      └─ NEEDS_HUMAN → escalation_node
   → audit_log_node (runs after every single node, not just at the end)
```

Key design rule you should hold me to: **the policy_node has zero LLM involvement.** It's a pure function of `(action, amount, confidence, retry_count, case_age, opt_out_flag)` against config values. This is the crux of "AI proposes, policy disposes" from your Section 11.

---

## 6. Tech Stack (justified for your skill level + your existing muscle memory)

You've already shipped Next.js/React + Prisma/PostgreSQL (Nexus OS) and a Node/React backend split (HireFlow). I'm deliberately reusing what you already know instead of introducing a third stack, except where Python is clearly the better tool (LangGraph, data science-flavored synthetic data generation).

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 14 (App Router) + TypeScript + Tailwind | You already know this from Nexus OS; fastest path to a polished dashboard |
| Charts | Recharts | Simple API, you've likely touched something similar |
| Backend API | **FastAPI (Python)** | LangGraph is Python-native; agent code, policy code, and evaluation scripts all live in one language instead of splitting logic across Node+Python |
| Agent orchestration | LangGraph | You listed it in your own experience; explicit state graph is exactly what a judge wants to see, not a black-box agent loop |
| Database | PostgreSQL (Neon, like Nexus OS) + SQLAlchemy | Relational schema is non-negotiable for this domain (Section 22); Neon is free-tier and you already have the workflow |
| LLM | Claude (Anthropic API) | Used *only* for diagnosis reasoning + strategy justification text + customer messages — never for policy decisions |
| Payments | Razorpay Node/Python SDK, TEST mode only | Official SDK — no invented endpoints |
| Auth | Simple JWT or Clerk (your call) | Keep this minimal — not the differentiator here |
| Evaluation | Plain Python script (`evaluation/run_evaluation.py`) | No framework needed; deterministic, fast, testable |
| Testing | Pytest (backend), Vitest/Jest (frontend) | Standard, you won't need to learn new tools |

**One important call I'm making now, as your senior engineer:** running FastAPI + Next.js as two separate services (not Next.js API routes) is the right call here — it keeps the agent/policy/evaluation code fully independent of the UI, testable in isolation, and runnable from the command line for judges (`python evaluation/run_evaluation.py`). This mirrors what real fintech recovery systems look like architecturally, and it avoids the Prisma/Edge-Runtime pain you hit on Nexus OS.

---

## 7. AI vs Deterministic — Component Split

| Component | Type | Why |
|---|---|---|
| Detection (failed/abandoned/overdue) | **Deterministic** | Pure SQL/rule conditions on timestamps and status — no ambiguity, must be reliable |
| Diagnosis | **Hybrid** — rules first, LLM only for the "unknown/ambiguous" bucket | Most failure reasons map directly from gateway codes; LLM adds value only on messy/unstructured cases |
| Recovery scoring | **Deterministic/statistical baseline first** | You must be able to say "this is a rule-based score," never falsely call it ML (Section 9) |
| Strategy selection | **LLM constrained to enum + rules fallback** | LLM picks from a fixed action list with structured output validation; if validation fails, fall back to a rule |
| Policy engine | **100% deterministic, no LLM** | This is the safety boundary — must be unconditionally reliable and auditable |
| Action execution | **Deterministic code calling Razorpay test API / simulation** | No reasoning needed here, just execution + idempotency check |
| Verification | **Deterministic** — checks actual payment/invoice status | Never trust the LLM's claim that something worked |
| Customer messages | **LLM** | This is where generation genuinely helps — natural, scenario-appropriate copy |

---

## 8. Data Model Overview

Core entities (full schema comes in Phase 3):

- `merchants`, `users` — auth/tenancy
- `customers` — with payment history rollups
- `transactions`, `payments` — the payment attempts and their outcomes
- `checkout_sessions` — abandoned-cart style events
- `invoices` — B2B receivables
- `subscriptions` — for the optional P2 scenario
- `revenue_risk_cases` — one row per detected case; central to everything downstream
- `diagnoses`, `recovery_scores`, `recovery_actions`, `action_results` — one row per agent-graph run, linked to the case
- `policies` — versioned config (Section 29), not hardcoded constants
- `escalations` — human-in-the-loop queue
- `promises_to_pay` — B2B follow-up tracking
- `audit_events` — append-only, foreign-keyed to case_id

Relationships: a `revenue_risk_case` is the hub — it links to exactly one source event (transaction/checkout_session/invoice, via a `case_type` + `source_id` pattern) and has a 1:many relationship to diagnoses/scores/actions/audit_events (since a case can be re-diagnosed or re-attempted over time, bounded by policy).

---

## 9. Razorpay Integration — Investigation Plan

Before Phase 15, I will (with you) verify against current Razorpay docs, not memory:
- What test-mode payment retry / recurring-payment capabilities actually exist today
- Whether Razorpay exposes a "payment link" or "invoice" API suitable for reminder flows in test mode
- Rate limits and test-mode constraints
- Exact required env vars and SDK version

I will **not** assume any specific endpoint exists until we look it up together in Phase 15 — this is exactly the "no invented endpoints" rule from Section 32/44, and I'll say "I cannot verify this" rather than guess if docs are ambiguous.

---

## 10. Risks & Technical Challenges

| Risk | Mitigation |
|---|---|
| LLM output breaking a financial action (hallucinated action type/amount) | Strict Pydantic/JSON-schema validation between every LLM node and the policy engine; invalid output = auto-reject + log, never silently retried as-is |
| Infinite retry loops | Policy engine hard caps + idempotency key per (case_id, action_type, attempt_number) |
| Fabricated "recovered" numbers | Recovery is only marked true after the verification node reads real payment/invoice status — never set by the strategy or action node directly |
| Scope creep into P2/P3 features before MVP is solid | Hold the line per Section 54 priority list — I'll push back if we drift |
| 10,000-row synthetic dataset performance in dashboard | Precompute batch evaluation to a results table; dashboard reads aggregates, not raw rows |
| You're mid-way through HireFlow AI already | This is a separate project — I'll keep them clearly separated in our conversations |

---

## 11. Development Roadmap (maps to your Section 41 phases)

Grouped into 5 milestones so the 20 phases don't feel overwhelming:

**Milestone A — Foundation (Phases 1–4):** architecture doc, env setup, DB schema + migrations, synthetic data generator (10k events, fixed seed)

**Milestone B — Core Agent Logic (Phases 5–9):** detection, scoring, diagnosis, strategy, policy engine — all testable via script/CLI before any UI exists

**Milestone C — Action & Trust Layer (Phases 10–13):** action executor + simulation layer, verification, audit trail, analytics aggregation

**Milestone D — Product Surface (Phases 14–15):** frontend dashboard, Razorpay test integration

**Milestone E — Proof & Polish (Phases 16–20):** automated tests, evaluation engine + baseline comparison, demo mode, UI polish, documentation

---

## 12. Difficulty Assessment

| Component | Difficulty | Notes |
|---|---|---|
| DB schema + synthetic data generator | Medium | Mechanical but needs realistic correlations (Section 21) |
| Detection layer | Easy | Straightforward SQL/rules |
| Policy engine | Medium | Simple logic, but must be bulletproof and well-tested |
| LangGraph agent graph | Medium–Hard | New framework for you; I'll walk through it node by node |
| Diagnosis/strategy LLM nodes + validation | Medium | Structured output + fallback logic is the tricky part |
| Action/verification/idempotency | Medium–Hard | Payment-adjacent code needs real care, even in simulation |
| Dashboard (Next.js) | Easy–Medium | You've done this shape of work before |
| Evaluation engine + baseline comparison | Medium | Needs discipline to keep numbers honest, not technically hard |
| Razorpay real test-mode integration | Medium | Mostly documentation-reading risk, not coding risk |

---

## 13. First Milestone (what "Phase 1 complete" looks like)

By the end of Phase 1 you should have:
- An `ARCHITECTURE.md` capturing the diagram above, finalized after your feedback
- Confirmed tech stack (or your adjustments to it)
- Project structure proposed (Section 40) — empty repo scaffolded, not filled
- Clear agreement on what's P0 vs P1/P2/P3 for *your* version of this build

No code yet in Phase 1 — that starts in earnest at Phase 2 (environment setup).

---

## Notes on how I'll work with you on this

- Complete file pastes, one command at a time in PowerShell, matching how we've worked before.
- I will not fabricate metrics, invent Razorpay endpoints, or call a simulated action "real" — I'll flag explicitly whenever something is TEST/SIMULATED vs REAL.
- I'll stop and ask before moving to the next phase, per your Section 41 workflow.

---

**When you're ready, say "START PHASE 1" and we'll begin the architecture + environment setup.**
