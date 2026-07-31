# test_pdf_parser.py
from app.parsers.pdf_parser import parse_pdf
import json

result = parse_pdf("C:\\Users\\admin\\Desktop\\Intern\\Task Intern-2.pdf")
print(f"Pages: {result['metadata']['page_count']}, Words: {result['metadata']['word_count']}")
print(f"Sections found: {len(result['sections'])}")
for s in result['sections'][:5]:
    print(f"  - {s['heading']!r} ({len(s['text'])} chars)")
print(f"Tables: {len(result['tables'])}, Figures: {len(result['images_or_figures'])}")