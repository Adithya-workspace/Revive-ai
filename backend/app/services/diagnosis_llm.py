"""
REVIVE AI — LLM Diagnosis for Ambiguous Cases (Phase 7)

Used only when deterministic rules can't confidently explain a case
(Section 8). Every LLM response is validated against a strict schema
before being trusted — invalid output is rejected, never partially
used (Section 34).

Model: Llama 3.3 70B via Groq. This is explicitly NOT Claude/Anthropic —
labeled accurately here and in docs/LIMITATIONS.md.
"""

import os
import json
from datetime import datetime, timezone
from pydantic import BaseModel, ValidationError, field_validator
from groq import Groq

GROQ_MODEL = "openai/gpt-oss-120b"

_client = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set in backend/.env")
        _client = Groq(api_key=api_key, timeout=20.0)  # never hang indefinitely
    return _client


class LLMDiagnosisOutput(BaseModel):
    """Strict schema the LLM's JSON output must match. Invalid output
    (wrong types, missing fields, out-of-range confidence) is rejected
    before it ever reaches the database or a downstream action."""

    diagnosis: str
    confidence: float
    evidence: list[str]
    recommended_next_step: str
    reasoning_summary: str

    @field_validator("confidence")
    @classmethod
    def confidence_in_range(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v


from app.constants import ALLOWED_ACTIONS as ALLOWED_NEXT_STEPS

SYSTEM_PROMPT = """You are a diagnosis component inside a revenue recovery system.
Your job is to explain WHY a specific piece of revenue is at risk, based only on
the structured context provided. You do not take any action yourself — you only
produce a diagnosis for a downstream system to review.

You MUST respond with ONLY a JSON object, no other text, no markdown formatting,
matching exactly this shape:

{
  "diagnosis": "a short (under 12 words) label for the root cause",
  "confidence": 0.0 to 1.0,
  "evidence": ["short factual observations from the context provided, 1-4 items"],
  "recommended_next_step": "ONE of: RETRY_PAYMENT, DELAYED_RETRY, SEND_PAYMENT_REMINDER, SEND_CHECKOUT_RECOVERY_MESSAGE, SEND_OVERDUE_REMINDER, TRACK_PROMISE_TO_PAY, ESCALATE_TO_HUMAN, STOP_RECOVERY_ATTEMPTS",
  "reasoning_summary": "1-2 sentences explaining your reasoning"
}

Be conservative with confidence — only use confidence above 0.7 if the evidence
is genuinely strong. If the context is thin or contradictory, say so and use a
lower confidence and recommend ESCALATE_TO_HUMAN.
"""


def _build_context_prompt(case_context: dict) -> str:
    return f"""Case context:
{json.dumps(case_context, indent=2, default=str)}

Respond with only the JSON object described in your instructions."""


def diagnose_with_llm(case_context: dict) -> dict:
    """
    Calls the LLM with the given case context, validates the response
    strictly, and returns a diagnosis dict in the same shape as the
    rules-based diagnoses. Raises an exception if the LLM call fails or
    the output doesn't validate — callers must handle this and fall
    back to a safe default (never silently trust unvalidated output).
    """
    client = _get_client()

    print(f"  → Calling Groq API (scenario: {case_context.get('scenario')})...", flush=True)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_context_prompt(case_context)},
        ],
        temperature=0.2,
        max_tokens=400,
    )

    raw_text = response.choices[0].message.content.strip()
    print(f"  ← Got response ({len(raw_text)} chars)", flush=True)

    # Strip markdown code fences if the model added them despite instructions
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:].strip()

    parsed_json = json.loads(raw_text)  # raises if not valid JSON
    validated = LLMDiagnosisOutput(**parsed_json)  # raises if schema doesn't match

    next_step = validated.recommended_next_step
    if next_step not in ALLOWED_NEXT_STEPS:
        # LLM invented an action outside our fixed registry — not allowed
        # per Section 10. Downgrade to the safest fallback instead of
        # trusting an unrecognized action.
        next_step = "ESCALATE_TO_HUMAN"

    return {
        "diagnosis": validated.diagnosis,
        "confidence": validated.confidence,
        "evidence": validated.evidence,
        "recommended_next_step": next_step,
        "reasoning_summary": validated.reasoning_summary,
        "diagnosis_source": "llm",
    }


def fallback_diagnosis(reason: str) -> dict:
    """
    Used when the LLM call fails or produces invalid output. Deliberately
    low-confidence and routes to human escalation — never guesses.
    """
    return {
        "diagnosis": "Unable to determine root cause automatically",
        "confidence": 0.30,
        "evidence": [reason],
        "recommended_next_step": "ESCALATE_TO_HUMAN",
        "reasoning_summary": (
            "Automated diagnosis failed or produced invalid output; "
            "routed to human review rather than guessing."
        ),
        "diagnosis_source": "llm",
    }