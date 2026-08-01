# tests/test_stage9.py
from dotenv import load_dotenv
load_dotenv()

from app.parsers import parse_document
from app.pipeline.stage2_classification import classify_document
from app.pipeline.stage3_knowledge_extraction import extract_knowledge
from app.pipeline.stage4_teaching_planner import plan_teaching_sequence
from app.pipeline.stage5_content_generation import generate_classroom_content
from app.pipeline.stage6_activity_generation import generate_activities
from app.pipeline.stage7_assessment_generation import generate_assessments
from app.pipeline.stage9_validation import validate_tkp
from tests.config import TEST_DOC_STEM
import json

parsed = parse_document(TEST_DOC_STEM)
classification = classify_document(parsed)
knowledge = extract_knowledge(parsed, classification)
plan = plan_teaching_sequence(knowledge, classification, target_periods=5, period_duration_minutes=40)
content = generate_classroom_content(plan, knowledge, classification)
activities = generate_activities(plan, content, classification)
assessments = generate_assessments(plan, classification)

report = validate_tkp(plan, knowledge, content, activities, assessments)
print(json.dumps(report, indent=2))