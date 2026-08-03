# app/pipeline/stage6_activity_generation.py
"""
Stage 6 — Activity Generation.
"""
import time
from app.llm_client import generate_json
from app.models import ActivitySpec, PeriodActivities, ActivityPlan
from app.utils import build_context_suffix

SYSTEM_PROMPT = """You are an expert instructional designer who turns brief
classroom activity ideas into complete, ready-to-run activity specifications
for teachers.

Given a period's short list of activity names/descriptions (already decided
— do not invent new activities, only elaborate the ones given), produce a
full spec for each one:
- name: keep close to the original activity description
- activity_type: classify it as one of "Demonstration", "Role Play",
  "Experiment", "Discussion", "Group Work", "Worksheet", "Simulation",
  "Game", or another concise type if none fit
- duration_minutes: a realistic duration that fits within the period's total
  time alongside the other activities
- materials_needed: concrete, obtainable materials (avoid vague items)
- teacher_instructions: clear step-by-step instructions a teacher could
  follow directly
- success_criteria: how the teacher can tell students engaged with/achieved
  the activity's purpose

Respond ONLY with a JSON object matching EXACTLY this structure:

{
  "period_number": <int>,
  "activities": [
    {
      "name": "string",
      "activity_type": "string",
      "duration_minutes": <int>,
      "materials_needed": ["string", ...],
      "teacher_instructions": "string",
      "success_criteria": "string"
    }
  ]
}
"""


def _generate_period_activities(period_number: int, activity_names: list,
                                 period_duration_minutes: int, classification: dict,
                                 curriculum_board: str = None, target_language: str = None) -> dict:
    context_suffix = build_context_suffix(curriculum_board, target_language)

    user_prompt = f"""Subject: {classification['subject']} | Grade: {classification['grade_level']}
Period {period_number}, total duration: {period_duration_minutes} minutes

Activity ideas to elaborate:
{activity_names}
{context_suffix}

Produce the full activity specifications as specified."""

    result = generate_json(SYSTEM_PROMPT, user_prompt, temperature=0.5, max_output_tokens=1024)
    result["period_number"] = period_number
    return PeriodActivities(**result).model_dump()


def generate_activities(teaching_plan: dict, classroom_content: dict, classification: dict,
                         curriculum_board: str = None, target_language: str = None) -> dict:
    content_by_period = {p["period_number"]: p for p in classroom_content["periods"]}

    period_results = []
    for period in teaching_plan["periods"]:
        period_number = period["period_number"]
        content = content_by_period.get(period_number)
        activity_names = content["classroom_activities"] if content else []

        if not activity_names:
            period_results.append(
                PeriodActivities(period_number=period_number, activities=[]).model_dump()
            )
            continue

        result = _generate_period_activities(
            period_number, activity_names, period["duration_minutes"], classification,
            curriculum_board, target_language
        )
        period_results.append(result)
        time.sleep(2)

    validated = ActivityPlan(periods=period_results)
    return validated.model_dump()