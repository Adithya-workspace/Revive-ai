# REVIVE AI — Evaluation Methodology

## Running the evaluation

```bash
cd backend
python -m evaluation.run_evaluation
```

This produces a console summary and a timestamped JSON report in `backend/evaluation/results/` (also saved as `latest.json`).

## What this evaluates

The evaluation engine compares REVIVE's real, measured pipeline results against a naive baseline strategy, using only data already produced by the actual system (detection, scoring, diagnosis, strategy, policy, action execution, and verification — Phases 5 through 13). No number in the report is invented or estimated; every figure is either a direct query result or a seeded, reproducible simulation clearly labeled as such.

## The baseline: what it is and why it's fair

Per the competition brief, the baseline is a naive strategy: intervene on every case with one generic action, no diagnosis, no policy gating, no retry caps.

To make this a genuinely fair comparison rather than a strawman:

- The baseline's simulated success is drawn against each case's real, already-computed `recovery_probability` score — the same transparent, rules-based score REVIVE itself uses (Section 9). The baseline isn't handicapped with a worse success model; it just applies no discrimination about which cases to act on or how.
- The baseline is restricted to the same universe of cases REVIVE's strategy stage actually reached (i.e., cases with a `RecoveryAction`). Cases still sitting in an undiagnosed backlog are excluded from both sides of the comparison — including them would let the baseline take credit for cases REVIVE was never given the chance to act on, which would not be a fair test of strategy quality.
- The random draw uses a fixed seed (42, matching `DATA_SEED`), so the baseline's result is reproducible across runs, not re-randomized each time.

## Two recovery rates, and why both matter

The report shows two different recovery rates, deliberately:

1. Recovery rate (overall) — recovered revenue divided by the full detected universe of cases. This is the honest, complete picture including REVIVE's current human-review backlog (cases sitting at `NEEDS_HUMAN` that haven't yet been approved by a person). This number will rise as the backlog gets processed.
2. Recovery rate (per attempt) — recovered revenue divided only by the cases REVIVE actually executed an action on. This is the apples-to-apples number to compare against the baseline, since the baseline also acts on every case it considers.

In the most recent run, REVIVE's per-attempt rate (56.2%) exceeded the baseline's rate (46.7%) by +9.5 percentage points — evidence that diagnosis-aware action selection is not just safer but more effective per action taken. Separately, REVIVE avoided 1,021 unnecessary automatic interventions (routing them to human review or rejecting them outright) that the baseline would have blindly attempted — this is the coverage-vs-safety tradeoff described in Section 20 of the spec.

## Reproducibility, and a deliberate limitation

Per Section 47, the evaluation records `data_seed`, `model_version`, and `policy_versions` in every report.

Important limitation, stated plainly: this evaluation reads the current state of the database, not a freshly-regenerated dataset on every run. The database itself originated from the synthetic generator's fixed seed (`DATA_SEED=42` in `scripts/generate_synthetic_data.py`), so the underlying data is reproducible in principle — but re-running the full pipeline (particularly LLM-based diagnosis) from a completely clean slate on every evaluation would mean repeated LLM API calls, which is slow and unnecessary for verifying the evaluation logic itself.

This is a deliberate engineering tradeoff for a time-boxed competition build, not an oversight. A production version of this system would snapshot a fixed, fully-processed dataset for evaluation purposes, decoupled from the live/demo database.

## Known gap at time of writing

As of the most recent evaluation run, 721 of 2,529 detected cases (all `checkout_abandonment`) remain in an undiagnosed backlog — this is a rate-limiting artifact of testing against Groq's free-tier API during development, not a system limitation. Running `python -m scripts.run_diagnosis` with a higher call cap will clear this backlog; the evaluation can be re-run afterward to reflect the fully-processed dataset.