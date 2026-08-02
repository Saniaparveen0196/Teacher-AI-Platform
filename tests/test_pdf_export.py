# tests/test_pdf_export.py
import json
from app.pdf_export import export_all_pdfs

with open("samples/sample_tkp_stem.json", "r", encoding="utf-8") as f:
    tkp = json.load(f)

paths = export_all_pdfs(tkp, "storage/outputs")
for name, path in paths.items():
    print(f"{name}: {path}")