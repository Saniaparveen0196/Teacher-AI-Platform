# test_stage1.py
from app.parsers import parse_document

for path in ["sample.pdf", "sample.docx", "sample.pptx", "sample.txt"]:
    try:
        result = parse_document(path)
        print(f"{path}: {len(result['sections'])} sections, {result['metadata']['word_count']} words")
    except FileNotFoundError:
        print(f"{path}: skipped (not found)")