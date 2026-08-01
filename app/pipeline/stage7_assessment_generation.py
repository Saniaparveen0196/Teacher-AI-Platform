# app/pipeline/stage7_assessment_generation.py
"""
Stage 7 — Assessment Generation.
One call per period (same reasoning as Stage 5/6). Numerical problems are
conditional — empty list for non-quantitative subjects, same rule as Stage 3's
formulae field.

If a response gets truncated before finishing every section (can happen on
dense periods, e.g. a consolidation period covering many concepts), missing
sections default to empty lists rather than crashing the whole pipeline run.
"""
import time
from app.llm_client import generate_json
from app.models import PeriodAssessment, AssessmentPlan

SYSTEM_PROMPT = """You are an expert assessment designer who creates fair,
well-calibrated classroom assessments.

Given a lesson period's objectives and covered concepts, generate a complete
assessment set for that period:
- mcqs: 3-5 multiple choice questions, each with exactly 4 options, one
  correct_answer that matches one option's text exactly, and a brief
  explanation of why it's correct.
- short_answer: 2-3 questions requiring a few sentences, each with a
  model_answer and a brief rubric describing what a full-credit answer needs.
- long_answer: 1-2 questions requiring a paragraph or more, each with a
  model_answer and rubric.
- numerical_problems: ONLY include if the subject is genuinely quantitative
  (math, physics, chemistry calculations, etc.) and this period covers
  calculable content. Otherwise return an EMPTY LIST — do not invent
  numerical problems for non-quantitative content (e.g. literature, history).
  Each problem needs solution_steps (worked solution) and final_answer.

Respond ONLY with a JSON object matching EXACTLY this structure:

{
  "period_number": <int>,
  "mcqs": [
    {"question": "string", "options": ["string","string","string","string"],
     "correct_answer": "string matching one option exactly", "explanation": "string"}
  ],
  "short_answer": [
    {"question": "string", "model_answer": "string", "rubric": "string"}
  ],
  "long_answer": [
    {"question": "string", "model_answer": "string", "rubric": "string"}
  ],
  "numerical_problems": [
    {"question": "string", "solution_steps": "string", "final_answer": "string"}
  ]
}
"""


def _fill_missing_sections(result: dict) -> dict:
    """If the model's response got truncated before finishing every
    section, default missing ones to empty lists rather than crashing —
    a thinner assessment for one period beats losing the whole pipeline run."""
    for field in ["mcqs", "short_answer", "long_answer", "numerical_problems"]:
        result.setdefault(field, [])
    return result


def _generate_period_assessment(period: dict, classification: dict) -> dict:
    user_prompt = f"""Subject: {classification['subject']} | Grade: {classification['grade_level']}
Category: {classification['category']}

Period {period['period_number']}: {period['title']}
Learning objectives: {period['learning_objectives']}
Concepts covered: {period['concepts_covered']}

Generate the complete assessment set as specified."""

    result = generate_json(SYSTEM_PROMPT, user_prompt, temperature=0.4, max_output_tokens=3072)
    result["period_number"] = period["period_number"]
    result = _fill_missing_sections(result)
    return PeriodAssessment(**result).model_dump()


def generate_assessments(teaching_plan: dict, classification: dict) -> dict:
    period_results = []
    for period in teaching_plan["periods"]:
        result = _generate_period_assessment(period, classification)
        period_results.append(result)
        time.sleep(2)

    validated = AssessmentPlan(periods=period_results)
    return validated.model_dump()