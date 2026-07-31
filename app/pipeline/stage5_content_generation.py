# app/pipeline/stage5_content_generation.py
"""
Stage 5 — Classroom Content Generation.
Loops ONE call PER PERIOD (each period's content is large and mostly
independent, so batching all periods into one call would blow the token
budget). Only that period's relevant knowledge slice is sent per call.

Prior periods' mentor moments are passed forward so later periods don't
generate near-duplicate anecdotes — the one real cost of generating
periods independently instead of in one big call.
"""
import time
from app.llm_client import generate_json
from app.models import PeriodContent, ClassroomContent

SYSTEM_PROMPT = """You are an expert classroom teacher and instructional
content writer. Given a single lesson period's plan and the relevant subject
knowledge, generate complete, ready-to-use classroom content for that period.

Guidelines:
- entry_ticket: a short warm-up question/activity (2-3 min) tied to prior
  knowledge or today's hook.
- teacher_script: a natural, spoken-style script a teacher could actually
  read/paraphrase aloud while teaching this period's concepts.
- blackboard_notes: concise notes as they'd appear written on a blackboard
  (bullet points, key terms, diagrams described in words).
- classroom_activities: 1-3 short activity descriptions appropriate to the
  duration (these will be elaborated with materials/instructions later).
- checkpoint_questions: 2-4 quick comprehension checks to ask mid-lesson.
- exit_ticket: a short question students answer before leaving, to gauge
  understanding of today's objectives.
- homework: a short take-home task connected to today's content.
- mentor_moment: a brief, genuine motivational anecdote or real-world
  connection relevant to the topic (not generic filler). If prior periods'
  mentor moments are listed as already used, you MUST pick a genuinely
  different angle, story, or connection — do not rephrase the same idea.

Respond ONLY with a JSON object matching EXACTLY this structure:

{
  "period_number": <int>,
  "entry_ticket": "string",
  "teacher_script": "string",
  "blackboard_notes": "string",
  "classroom_activities": ["string", ...],
  "checkpoint_questions": ["string", ...],
  "exit_ticket": "string",
  "homework": "string",
  "mentor_moment": "string"
}
"""


def _relevant_knowledge_slice(period: dict, knowledge: dict) -> dict:
    """Only pull concepts/definitions/examples this period actually covers,
    keeping each call's input small."""
    covered = set(c.lower() for c in period["concepts_covered"])

    concepts = [c for c in knowledge["concepts"] if c["name"].lower() in covered]
    definitions = [d for d in knowledge["definitions"]
                   if any(term in d["term"].lower() or d["term"].lower() in term for term in covered)]
    examples = [e for e in knowledge["examples"]
                if e.get("relates_to_concept") and e["relates_to_concept"].lower() in covered]

    return {"concepts": concepts, "definitions": definitions, "examples": examples}


def _generate_single_period_content(period: dict, knowledge: dict, classification: dict,
                                     used_mentor_moments: list) -> dict:
    slice_ = _relevant_knowledge_slice(period, knowledge)

    avoid_note = ""
    if used_mentor_moments:
        avoid_note = (
            "\n\nAlready used mentor moments in earlier periods (do NOT repeat "
            "these ideas, pick a genuinely different angle):\n"
            + "\n".join(f"- {m[:150]}" for m in used_mentor_moments)
        )

    user_prompt = f"""Subject: {classification['subject']} | Grade: {classification['grade_level']}

Period {period['period_number']}: {period['title']} ({period['duration_minutes']} min)
Learning objectives for this period: {period['learning_objectives']}

Relevant concepts: {slice_['concepts']}
Relevant definitions: {slice_['definitions']}
Relevant examples: {slice_['examples']}
{avoid_note}

Generate the complete classroom content for this period as specified."""

    result = generate_json(SYSTEM_PROMPT, user_prompt, temperature=0.6, max_output_tokens=1536)
    result["period_number"] = period["period_number"]  # guard in case the model omits/misplaces it
    return PeriodContent(**result).model_dump()


def generate_classroom_content(teaching_plan: dict, knowledge: dict, classification: dict) -> dict:
    period_contents = []
    used_mentor_moments = []

    for period in teaching_plan["periods"]:
        content = _generate_single_period_content(period, knowledge, classification, used_mentor_moments)
        period_contents.append(content)
        used_mentor_moments.append(content["mentor_moment"])
        time.sleep(2)  # small pacing gap between calls to stay under per-minute token limits

    validated = ClassroomContent(periods=period_contents)
    return validated.model_dump()