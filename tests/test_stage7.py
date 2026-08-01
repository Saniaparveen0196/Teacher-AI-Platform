# tests/test_stage7.py
from dotenv import load_dotenv
load_dotenv()

from app.parsers import parse_document
from app.pipeline.stage2_classification import classify_document
from app.pipeline.stage3_knowledge_extraction import extract_knowledge
from app.pipeline.stage4_teaching_planner import plan_teaching_sequence
from app.pipeline.stage7_assessment_generation import generate_assessments
import json

parsed = parse_document(r"C:\Users\admin\Desktop\Intern\samples\chapter4.pdf")
classification = classify_document(parsed)
knowledge = extract_knowledge(parsed, classification)
plan = plan_teaching_sequence(knowledge, classification, target_periods=5, period_duration_minutes=40)
assessments = generate_assessments(plan, classification)
print(json.dumps(assessments, indent=2))