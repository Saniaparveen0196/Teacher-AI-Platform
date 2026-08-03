# app/parsers/__init__.py — UPDATED

import os
from .pdf_parser import parse_pdf
from .docx_parser import parse_docx
from .pptx_parser import parse_pptx
from .txt_parser import parse_txt


def parse_document(file_path: str, document_nature_hint: str = None) -> dict:
    """
    document_nature_hint: optional user-provided hint ("Mostly Text",
    "Scanned PDF", "I'm Not Sure", etc.) per the assignment FAQ's
    cost-aware routing guidance. Only affects PDF parsing currently —
    other formats don't have a scanned-vs-native distinction.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        force_ocr = (document_nature_hint == "Scanned PDF")
        return parse_pdf(file_path, force_ocr=force_ocr)
    elif ext == ".docx":
        return parse_docx(file_path)
    elif ext == ".pptx":
        return parse_pptx(file_path)
    elif ext in (".txt", ".md"):
        return parse_txt(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")