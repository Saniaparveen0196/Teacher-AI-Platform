# test_stage4.py
from dotenv import load_dotenv
load_dotenv()

from app.parsers import parse_document
from app.pipeline.stage2_classification import classify_document
from app.pipeline.stage3_knowledge_extraction import extract_knowledge
from app.pipeline.stage4_teaching_planner import plan_teaching_sequence
import json

parsed = parse_document("C:\\Users\\admin\\Desktop\\Intern\\chapter4.pdf")  # not the assignment PDF
classification = classify_document(parsed)
knowledge = extract_knowledge(parsed, classification)
plan = plan_teaching_sequence(knowledge, classification, target_periods=5, period_duration_minutes=40)
print(json.dumps(plan, indent=2))