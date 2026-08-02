# app/orchestrator.py
"""
Orchestrator — runs Stages 1-9 in sequence, threading each stage's output
into the next, and yields progress events as it goes.

This is a generator, not a plain function: each `yield` is one progress
update. This maps directly onto the brief's Streaming Progress API
requirement, and later becomes one SSE message per yield in the FastAPI
layer with almost no translation needed.
"""
from datetime import datetime, timezone

from app.parsers import parse_document
from app.pipeline.stage2_classification import classify_document
from app.pipeline.stage3_knowledge_extraction import extract_knowledge
from app.pipeline.stage4_teaching_planner import plan_teaching_sequence
from app.pipeline.stage5_content_generation import generate_classroom_content
from app.pipeline.stage6_activity_generation import generate_activities
from app.pipeline.stage7_assessment_generation import generate_assessments
from app.pipeline.stage8_gap_analysis import analyze_learning_gaps
from app.pipeline.stage9_validation import validate_tkp
from app.models import TeacherKnowledgePackage, TKPMetadata

# (stage_name, progress_percent_after_this_stage) — used to emit consistent
# progress values regardless of how long each stage actually takes.
_STAGE_PROGRESS = {
    "document_intelligence": 10,
    "educational_classification": 20,
    "knowledge_extraction": 30,
    "teaching_planner": 40,
    "classroom_content_generation": 60,   # heavier stage (5 LLM calls), bigger jump
    "activity_generation": 70,
    "assessment_generation": 80,
    "learning_gap_analysis": 90,
    "validation": 95,
    "publishing": 100,
}


def _progress_event(stage: str, message: str = ""):
    return {"stage": stage, "progress": _STAGE_PROGRESS[stage], "message": message}


def run_pipeline(file_path: str, source_filename: str,
                  target_periods: int = 5, period_duration_minutes: int = 40):
    """
    Generator. Yields progress dicts throughout, and a final dict of the
    shape {"stage": "publishing", "progress": 100, "result": <TKP dict>}
    once the full TeacherKnowledgePackage is assembled and validated.
    """
    yield _progress_event("document_intelligence", "Parsing document...")
    parsed = parse_document(file_path)

    yield _progress_event("educational_classification", "Classifying document...")
    classification = classify_document(parsed)

    yield _progress_event("knowledge_extraction", "Extracting knowledge...")
    knowledge = extract_knowledge(parsed, classification)

    yield _progress_event("teaching_planner", "Building teaching plan...")
    teaching_plan = plan_teaching_sequence(
        knowledge, classification, target_periods, period_duration_minutes
    )

    yield _progress_event("classroom_content_generation", "Generating classroom content...")
    classroom_content = generate_classroom_content(teaching_plan, knowledge, classification)

    yield _progress_event("activity_generation", "Generating activities...")
    activity_plan = generate_activities(teaching_plan, classroom_content, classification)

    yield _progress_event("assessment_generation", "Generating assessments...")
    assessment_plan = generate_assessments(teaching_plan, classification)

    yield _progress_event("learning_gap_analysis", "Analyzing learning gaps...")
    gap_analysis = analyze_learning_gaps(teaching_plan, knowledge, classification)

    yield _progress_event("validation", "Validating output...")
    validation_report = validate_tkp(
        teaching_plan, knowledge, classroom_content, activity_plan, assessment_plan
    )

    yield _progress_event("publishing", "Packaging final output...")
    tkp = TeacherKnowledgePackage(
        metadata=TKPMetadata(
            source_filename=source_filename,
            generated_at=datetime.now(timezone.utc).isoformat(),
            target_periods=target_periods,
            period_duration_minutes=period_duration_minutes,
        ),
        classification=classification,
        knowledge=knowledge,
        teaching_plan=teaching_plan,
        classroom_content=classroom_content,
        activity_plan=activity_plan,
        assessment_plan=assessment_plan,
        gap_analysis=gap_analysis,
        validation_report=validation_report,
    )

    yield {"stage": "publishing", "progress": 100, "result": tkp.model_dump()}