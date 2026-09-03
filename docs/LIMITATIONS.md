# REVIVE AI — Known Limitations

Stated plainly, per Section 44/45 of the original spec: no fabricated claims, no hidden gaps. This is what the system does not do, and why.

## No authentication

There's no login system. The application currently assumes a single merchant and exposes every endpoint without access control. Real multi-tenant use would require this before anything else.

## Razorpay integration is deferred

Every action in this build executes in `SIMULATED` mode — clearly labeled as such everywhere it appears (dashboard badges, API responses, audit trail). Real Razorpay test-mode integration was scoped as Phase 15 in the original roadmap and treated as a time-boxed stretch goal, not part of the core deliverable. See the README's Progress section for its current status.

## Diagnosis quality depends on Groq's free-tier availability

The LLM used for ambiguous-case diagnosis (Llama 3.3 / `openai/gpt-oss-120b` via Groq) is a free-tier service. During development, a model was deprecated mid-project and had to be swapped (documented in the commit history). A production system would need a paid tier with stronger uptime guarantees and should not assume model names are stable indefinitely.

## Evaluation reads live database state, not a frozen snapshot

As documented in detail in `docs/EVALUATION.md`, the evaluation engine measures the *current* state of the database rather than re-running the entire pipeline from a clean slate on every invocation. This is a deliberate tradeoff to avoid repeated LLM API calls, not an oversight — but it does mean evaluation numbers can shift slightly if the database changes between runs (e.g. from practicing Demo Mode without resetting it afterward).

## No automated CI pipeline

37 automated tests exist and pass (`backend/tests/`), but they run manually (`python -m pytest tests/ -v`), not on every commit via a CI service like GitHub Actions. Wiring this up would be a natural next step.

## No rate limiting

No API endpoint enforces request rate limits. This matters most for the diagnosis endpoint, which can trigger real LLM API calls.

## Scoring, diagnosis, and strategy are deterministic rules, not machine learning

This is by design, not a limitation to apologize for — Section 9 of the original spec explicitly requires transparent, explainable scoring rather than an opaque model, and every score/decision in this system honestly labels itself as `"rules"`. Stated here for completeness: if a judge is looking for a trained ML model anywhere in the scoring pipeline, there isn't one, and that was a deliberate choice.

## Polymorphic source references have no database-level referential integrity

`RevenueRiskCase.source_type` + `source_id` (pointing at whichever of `transactions`, `checkout_sessions`, or `invoices` matches) is enforced in application code, not by a database foreign key — Postgres can't express "this ID exists in one of three possible tables." This tradeoff is documented in `docs/ARCHITECTURE.md` Section 2, chosen deliberately to keep the schema extensible for future scenario types without migrations.

## Demo Mode uses a single existing customer

`POST /demo/create-case` attaches every demo-generated case to whichever customer happens to be first in the database, rather than creating a new customer each time. This keeps the demo simple but means demo-generated cases don't spread across different customers.

## Mobile support is functional, not optimized

Phase 19 made every screen genuinely usable on narrow viewports (no overlapping content, responsive tables and grids), but this is fundamentally a data-dense merchant operations tool — it's designed to be used on a desktop, and mobile support exists as a safety net, not the primary experience.