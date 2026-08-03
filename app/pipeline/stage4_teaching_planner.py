# app/pipeline/stage4_teaching_planner.py
"""
Stage 4 — Teaching Planner.
Converts extracted knowledge into a multi-period teaching sequence.
"""
from app.llm_client import generate_json
from app.models import TeachingPlan
from app.utils import build_context_suffix

SYSTEM_PROMPT = """You are an expert instructional designer who plans
multi-period teaching sequences for classroom teachers.

Given a full structured knowledge extraction (learning objectives,
prerequisites, concepts, definitions, examples, etc.) for a topic, produce a
pedagogically sound multi-period teaching plan.

Sequencing principles you MUST follow:
- Foundational/prerequisite concepts come before concepts that depend on them.
- Each period should have a coherent, achievable set of objectives for its
  duration — do not cram unrelated concepts into one period just to reduce
  period count.
- Later periods should build on earlier ones, not repeat them.
- Propose a period count appropriate to the volume and complexity of the
  content (use the suggested period count as a target, but you may deviate
  slightly if the content genuinely needs more/fewer periods).
- Every concept and learning objective from the input SHOULD be covered by
  at least one period — do not drop content.

Respond ONLY with a JSON object matching EXACTLY this structure:

{
  "total_periods": <int>,
  "periods": [
    {
      "period_number": <int, starting at 1>,
      "title": "string",
      "duration_minutes": <int>,
      "learning_objectives": ["string", ...],
      "concepts_covered": ["string", ...],
      "sequencing_rationale": "string explaining why this content is placed here"
    }
  ],
  "overall_sequencing_notes": "string explaining the overall pedagogical flow"
}
"""


def plan_teaching_sequence(knowledge: dict, classification: dict,
                            target_periods: int = 5, period_duration_minutes: int = 40,
                            curriculum_board: str = None, target_language: str = None) -> dict:
    context_suffix = build_context_suffix(curriculum_board, target_language)

    user_prompt = f"""Topic: {classification['topic']}
Subject: {classification['subject']}
Grade level: {classification['grade_level']}
Difficulty: {classification['difficulty']}

Target: approximately {target_periods} periods of {period_duration_minutes} minutes each
(you may adjust the count if the content genuinely calls for it).

Learning objectives:
{knowledge['learning_objectives']}

Prerequisites:
{knowledge['prerequisites']}

Concepts (name: explanation):
{[(c['name'], c['explanation']) for c in knowledge['concepts']]}

Definitions (terms only, for reference): {[d['term'] for d in knowledge['definitions']]}
{context_suffix}

Produce the multi-period teaching plan as specified."""

    result = generate_json(SYSTEM_PROMPT, user_prompt, temperature=0.4, max_output_tokens=8192)
    validated = TeachingPlan(**result)
    return validated.model_dump()