# app/pipeline/stage8_gap_analysis.py
"""
Stage 8 — Learning Gap Analysis.
Builds on Stage 3's common_misconceptions (topic-inherent) by adding
actionability per period: diagnostic questions, severity, remedial actions.
Same one-call-per-period pattern as Stages 5-7.
"""
import time
from app.llm_client import generate_json
from app.models import PeriodGapAnalysis, GapAnalysisReport

SYSTEM_PROMPT = """You are an expert educational diagnostician who identifies
where students commonly go wrong and designs ways for teachers to catch and
fix those gaps early.

Given a lesson period's concepts and a list of misconceptions already known
to be associated with this topic (from prior analysis), produce an
actionable gap analysis for THIS specific period:

For each relevant misconception (only ones actually relevant to this
period's concepts_covered — do not include misconceptions unrelated to what
this period teaches):
- misconception: restate it clearly
- diagnostic_question: a specific question a teacher could ask in class to
  reveal whether a student holds this misconception
- severity: "Low", "Medium", or "High" — how much this misconception would
  undermine understanding of later material if left uncorrected
- remedial_action: a concrete, practical step the teacher can take if this
  gap is detected (not vague advice like "review the concept" — be specific,
  e.g. what analogy, demonstration, or re-explanation to use)

If none of the known misconceptions are relevant to this period, you may
identify 1-2 NEW likely misconceptions specific to this period's concepts
instead. Every period should have at least 1 gap identified.

Respond ONLY with a JSON object matching EXACTLY this structure:

{
  "period_number": <int>,
  "gaps": [
    {
      "misconception": "string",
      "diagnostic_question": "string",
      "severity": "Low" | "Medium" | "High",
      "remedial_action": "string"
    }
  ]
}
"""


def _generate_period_gaps(period: dict, known_misconceptions: list, classification: dict) -> dict:
    covered = set(c.lower() for c in period["concepts_covered"])
    relevant_known = [
        m for m in known_misconceptions
        if any(concept in m["misconception"].lower() or m["misconception"].lower() in concept
               for concept in covered)
    ]

    user_prompt = f"""Subject: {classification['subject']} | Grade: {classification['grade_level']}

Period {period['period_number']}: {period['title']}
Concepts covered: {period['concepts_covered']}
Learning objectives: {period['learning_objectives']}

Known misconceptions associated with this topic (from prior document analysis):
{relevant_known if relevant_known else "None specifically matched — identify likely ones yourself."}

Generate the gap analysis for this period as specified."""

    result = generate_json(SYSTEM_PROMPT, user_prompt, temperature=0.4, max_output_tokens=1024)
    result["period_number"] = period["period_number"]
    return PeriodGapAnalysis(**result).model_dump()


def analyze_learning_gaps(teaching_plan: dict, knowledge: dict, classification: dict) -> dict:
    known_misconceptions = knowledge.get("common_misconceptions", [])

    period_results = []
    for period in teaching_plan["periods"]:
        result = _generate_period_gaps(period, known_misconceptions, classification)
        period_results.append(result)
        time.sleep(2)

    validated = GapAnalysisReport(periods=period_results)
    return validated.model_dump()