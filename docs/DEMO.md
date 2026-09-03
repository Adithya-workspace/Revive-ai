# REVIVE AI — Demo Guide

## Fastest path: the live Demo Mode page

The application includes a built-in guided walkthrough — no terminal required for a judge to see everything in action.

1. Start the backend: `cd backend && venv\Scripts\Activate.ps1 && uvicorn app.main:app --reload --port 8081`
2. Start the frontend: `cd frontend && npm run dev`
3. Open `http://localhost:3000/demo`
4. Click each numbered step in order (1 through 11). Each one calls the real backend and shows a real result — nothing here is scripted or faked.

What this proves, step by step:
- **Step 1-2** — a fresh case is created and immediately detected by real deterministic rules.
- **Step 3-4** — the case is scored (explicitly labeled "rules," not ML) and diagnosed (rules first, LLM only for genuinely ambiguous cases).
- **Step 5-6** — a strategy is proposed, then the policy engine independently authorizes, defers, or rejects it — visibly, with a stated reason.
- **Step 7-8** — only approved actions execute (labeled `SIMULATED`), and a case is only ever marked recovered after real verification.
- **Step 9** — a deliberate infrastructure failure is simulated, proving the system never falsely marks a case recovered and never duplicates an action.
- **Step 10-11** — the audit trail shows everything that just happened, and a live evaluation compares REVIVE's real results against a naive baseline.

**Before judging/recording, click "Reset Demo Data"** (step 0) to remove anything created during practice runs, so the numbers you present match the official ones in the README.

## Exploring beyond the guided walkthrough

- **Dashboard** (`/`) — overall KPIs across the full 2,529-case synthetic dataset
- **Revenue at Risk** (`/revenue-at-risk`) — the filterable case table
- **Case Detail** — click any case ID anywhere to see its complete story: diagnosis, strategy, policy reasoning, action result, and audit trail in one place
- **Escalations** (`/escalations`) — the human review queue; click into a case and use the Approve/Reject buttons directly
- **Analytics** (`/analytics`) — charts built from real aggregated data
- **Settings** (`/settings`) — the actual policy values governing every automatic decision, read live from the database

## Getting the official, reproducible evaluation numbers

The numbers quoted in the README come from the CLI evaluation engine, run against the fully-processed dataset before any demo practice:

```bash
cd backend
python -m evaluation.run_evaluation
```

This is the same logic exposed live via the Demo Mode page's "Run Full Evaluation" button, but writes a timestamped JSON report to `backend/evaluation/results/` for a permanent record. See `docs/EVALUATION.md` for the full methodology.