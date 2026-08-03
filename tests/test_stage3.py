# test_stage3.py
from dotenv import load_dotenv
load_dotenv()

from app.parsers import parse_document
from app.pipeline.stage2_classification import classify_document
from app.pipeline.stage3_knowledge_extraction import extract_knowledge
import json

parsed = parse_document("C:\\Users\\admin\\Desktop\\Intern\\samples\\history -chapter 3.pdf")
classification = classify_document(parsed)
knowledge = extract_knowledge(parsed, classification)
print(json.dumps(knowledge, indent=2))