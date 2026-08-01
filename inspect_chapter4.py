# inspect_chapter4.py
from app.parsers import parse_document

parsed = parse_document(r"C:\Users\admin\Desktop\Intern\samples\chapter4.pdf")
print(f"Word count: {parsed['metadata']['word_count']}")
print(f"Sections: {len(parsed['sections'])}")
for s in parsed['sections'][:10]:
    print(f"  - {s['heading']!r} ({len(s['text'])} chars)")
print("\n--- First 800 chars of raw_text ---")
print(parsed['raw_text'][:800])