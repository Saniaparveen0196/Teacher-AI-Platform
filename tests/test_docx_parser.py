# test_docx_parser.py
from app.parsers.docx_parser import parse_docx

result = parse_docx(r"C:\Users\admin\Desktop\Intern\Sania_Parveen_Resume_AIML (3).docx")
print(f"Words: {result['metadata']['word_count']}")
print(f"Sections found: {len(result['sections'])}")
for s in result['sections'][:8]:
    print(f"  - {s['heading']!r} (level {s['level']}, {len(s['text'])} chars)")
print(f"Tables: {len(result['tables'])}, Figures: {result['images_or_figures']}")