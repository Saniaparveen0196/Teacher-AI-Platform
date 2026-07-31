# test_stage2.py
from dotenv import load_dotenv
load_dotenv()

from app.parsers import parse_document
from app.pipeline.stage2_classification import classify_document
import json

parsed = parse_document("C:\\Users\\admin\\Desktop\\Intern\\Task Intern-2.pdf")
classification = classify_document(parsed)
print(json.dumps(classification, indent=2))