# tests/test_stage8.py
from dotenv import load_dotenv
load_dotenv()

from app.parsers import parse_document
from app.pipeline.stage2_classification import classify_document
from app.pipeline.stage3_knowledge_extraction import extract_knowledge
from app.pipeline.stage4_teaching_planner import plan_teaching_sequence
from app.pipeline.stage8_gap_analysis import analyze_learning_gaps
from tests.config import TEST_DOC_STEM
import json

parsed = parse_document(TEST_DOC_STEM)
classification = classify_document(parsed)
knowledge = extract_knowledge(parsed, classification)
plan = plan_teaching_sequence(knowledge, classification, target_periods=5, period_duration_minutes=40)
gaps = analyze_learning_gaps(plan, knowledge, classification)
print(json.dumps(gaps, indent=2))