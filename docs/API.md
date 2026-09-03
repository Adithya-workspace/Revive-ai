# REVIVE AI — API Reference

The backend is a FastAPI application. Full interactive documentation (try-it-out, request/response schemas) is auto-generated and available at:

```
http://localhost:8081/docs
```

This document is a human-readable map of what exists and why, organized by pipeline stage — useful for understanding the system without running it.

---

## Pipeline stage endpoints

Each of these mirrors a CLI script of the same name (`backend/scripts/run_*.py`) — the API and CLI call the exact same underlying service functions, so results are identical regardless of how they're triggered.

| Method | Path | Purpose |
|---|---|---|
| POST | /detection/run-scan/{merchant_id} | Runs deterministic detection rules (Phase 5) across transactions, checkout sessions, and invoices. Idempotent. |
| POST | /scoring/run/{merchant_id} | Recalculates recovery probability for all open cases using the rules-based formula (Phase 6). |
| POST | /diagnosis/run/{merchant_id}?max_llm_calls=N | Diagnoses undiagnosed cases — rules first, LLM (Groq) only for genuinely ambiguous cases, capped by max_llm_calls. |
| POST | /strategy/run/{merchant_id} | Applies override rules on top of each case's diagnosis to select a final action (Phase 8). No LLM calls. |
| POST | /policy/run/{merchant_id} | THE safety boundary. Authorizes (APPROVED), defers (NEEDS_HUMAN), or blocks (REJECTED) each proposed action. Zero LLM involvement. |
| POST | /actions/run/{merchant_id} | Executes only APPROVED actions. All results are labeled SIMULATED (Phase 15 defers real Razorpay calls). |
| POST | /verification/run/{merchant_id} | The only stage allowed to mark a case recovered — confirms the real outcome before updating status. |

## Case & data browsing endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | /merchants | Lists merchants. |
| GET | /cases/{merchant_id} | Filterable, paginated case list (status, scenario, priority). |
| GET | /cases/{merchant_id}/{case_id} | Full case detail: customer, diagnosis, strategy, policy, action result, audit trail. |
| POST | /cases/{merchant_id}/{case_id}/human-decision | Human-in-the-loop endpoint — approves or rejects an action currently at NEEDS_HUMAN. Only valid from that state. |
| GET | /customers/{merchant_id} | Customer list with case-history rollups. |
| GET | /customers/{merchant_id}/{customer_id} | Single customer detail with transaction/case history. |
| GET | /actions/{merchant_id} | All recovery actions, filterable by action type or policy decision. |
| GET | /escalations/{merchant_id} | Cases currently sitting at NEEDS_HUMAN — the human review queue. |
| GET | /policies | Lists all configured policy values (versioned, admin-visible per Section 29). |
| GET | /audit-events/{merchant_id} | Searchable audit log, filterable by event type or case. |
| GET | /analytics/{merchant_id} | Full aggregate dashboard metrics (Phase 13). |

## Demo Mode endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | /demo/create-case/{merchant_id} | Seeds one fresh, unprocessed source record so pipeline-stage buttons have live work to demonstrate. Tracked separately from the real synthetic dataset. |
| POST | /demo/reset/{merchant_id} | Removes every record create-case has produced, restoring official metrics exactly. |
| POST | /demo/run-evaluation/{merchant_id} | Same logic as python -m evaluation.run_evaluation, callable live without a terminal. |
| POST | /actions/simulate-api-failure/{merchant_id} | Deliberately fails an action execution to demonstrate graceful failure handling (Section 17) — proves idempotency, that a case is never falsely marked recovered, and that infra failures are logged distinctly from customer declines. |

---

## Design notes worth knowing

- Read endpoints (GET) never mutate anything and are safe to call freely.
- Write endpoints (POST) that run pipeline stages are idempotent — re-running any of them only processes new/unprocessed records, never duplicates work.
- No authentication is implemented. See docs/SECURITY.md and docs/LIMITATIONS.md for what this means and why, given the project's scope.
- CORS is configured to allow only http://localhost:3000 (the frontend's dev origin) — see backend/app/main.py.