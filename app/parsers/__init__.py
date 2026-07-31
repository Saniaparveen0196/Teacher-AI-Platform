# app/parsers/__init__.py
"""
Stage 1 — Document Intelligence: format dispatcher.
Every downstream stage imports parse_document() from here and never touches
a format-specific parser directly.
"""
import os
from .pdf_parser import parse_pdf
from .docx_parser import parse_docx
from .pptx_parser import parse_pptx
from .txt_parser import parse_txt


def parse_document(file_path: str) -> dict:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return parse_pdf(file_path)
    elif ext == ".docx":
        return parse_docx(file_path)
    elif ext == ".pptx":
        return parse_pptx(file_path)
    elif ext in (".txt", ".md"):
        return parse_txt(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")