# test_stage6.py
from dotenv import load_dotenv
load_dotenv()

from app.parsers import parse_document
from app.pipeline.stage2_classification import classify_document
from app.pipeline.stage3_knowledge_extraction import extract_knowledge
from app.pipeline.stage4_teaching_planner import plan_teaching_sequence
from app.pipeline.stage5_content_generation import generate_classroom_content
from app.pipeline.stage6_activity_generation import generate_activities
import json

parsed = parse_document("C:\\Users\\admin\\Desktop\\Intern\\chapter4.pdf")
classification = classify_document(parsed)
knowledge = extract_knowledge(parsed, classification)
plan = plan_teaching_sequence(knowledge, classification, target_periods=5, period_duration_minutes=40)
content = generate_classroom_content(plan, knowledge, classification)
activities = generate_activities(plan, content, classification)
print(json.dumps(activities, indent=2))