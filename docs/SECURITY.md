# REVIVE AI — Security Notes

This document is an honest account of what security practices this build follows, and what it deliberately does not implement, given its scope as a competition prototype.

## What's implemented

- **Secrets never hardcoded.** All credentials (`DATABASE_URL`, `GROQ_API_KEY`, and the placeholder Razorpay keys) live in `backend/.env`, which is gitignored. `.env.example` holds only placeholder text — never real values.
- **No secrets reach the frontend.** The only environment variable exposed to the browser is `NEXT_PUBLIC_API_URL`, a plain localhost address — no API keys, no database credentials.
- **Server-side policy enforcement.** Every action that could touch money or contact a customer passes through the policy engine (`backend/app/policies/engine.py`) — a pure, deterministic function with no LLM involvement, enforced on the backend, never trusted from client input.
- **Input validation via Pydantic.** All request bodies (e.g. the human-decision endpoint) are validated against explicit schemas before being processed.
- **Idempotency on every action.** A unique database constraint (`ActionResult.recovery_action_id`) plus application-level checks prevent duplicate execution — verified by automated tests (`backend/tests/test_pipeline.py`).
- **LLM output is never trusted directly.** Every LLM response is validated against a strict Pydantic schema (`LLMDiagnosisOutput`) before being used; invalid or unparseable output is rejected and routed to a safe fallback, never partially trusted.
- **CORS is scoped**, not wide open — restricted to the frontend's dev origin in `backend/app/main.py`.

## What's explicitly not implemented (and why that's stated plainly here)

- **No user authentication or authorization.** There is no login system, no user accounts, no session management. Every API endpoint is currently reachable by anyone who can reach the server. This is appropriate for a local competition demo but would be a hard blocker for any real deployment — see `LIMITATIONS.md`.
- **No rate limiting** on API endpoints. A real production system would need this, particularly on any endpoint that triggers an LLM call.
- **No encryption beyond what Neon provides by default** for data at rest. No field-level encryption for customer PII (names, emails, phone numbers) in the synthetic dataset.
- **A real secret did briefly exist in a committed file during development** (a Groq API key was accidentally pasted into `backend/.env.example` instead of the real `.env`). GitHub's push protection caught this before it reached the remote repository, and the key was rotated immediately as a precaution. This is disclosed here rather than hidden, as an example of the discipline the project tries to hold itself to.

## Payment-specific safety (Section 33 of the original spec)

- **Double-retry / duplicate-payment protection**: enforced via the unique constraint on `ActionResult` and the retry-count check in the policy engine (`max_automatic_retries`).
- **Infinite retry loop protection**: the policy engine's retry cap is a hard, database-backed limit, not a suggestion — verified in `test_policy.py`.
- **No AI bypass of policy**: the policy engine (`backend/app/policies/engine.py`) contains zero LLM calls and zero imports from any diagnosis/strategy module — this is enforced by file structure, not just convention.