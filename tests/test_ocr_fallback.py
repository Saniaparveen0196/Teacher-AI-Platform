# tests/test_ocr_fallback.py
from dotenv import load_dotenv
load_dotenv()
from app.parsers import parse_document

parsed = parse_document(r"C:\Users\admin\Desktop\Intern\samples\chapter4.pdf")
print(f"Word count: {parsed['metadata']['word_count']}")
print(f"OCR pages used: {parsed['metadata']['ocr_pages_used']}")
print(f"Sections found: {len(parsed['sections'])}")
print("\n--- First 500 chars ---")
print(parsed['raw_text'][:500])