# app/parsers/pdf_parser.py
"""
Stage 1 — Document Intelligence: PDF parser.
Falls back to OCR (Tesseract) for pages where native text extraction
returns near-empty content — handles scanned PDFs, which the assignment
FAQ names as an expected real-world input (NCERT chapters are often
scanned). OCR is only invoked per-page, only when needed, to keep it
cost-aware rather than OCR-ing every page of every document by default.
"""
import os
import re
import pdfplumber
import pytesseract
from pdf2image import convert_from_path

# Configure external binary paths from env vars (set these in .env) —
# more reliable across machines/deployment than relying on system PATH.
TESSERACT_PATH = os.environ.get("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
POPPLER_PATH = os.environ.get("POPPLER_PATH", None)  # e.g. r"C:\poppler\poppler-24.xx.x\Library\bin"

if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

MIN_CHARS_BEFORE_OCR_FALLBACK = 40  # if native extraction returns less than this, treat page as scanned

HEADING_PATTERN = re.compile(
    r"^\s*("
    r"chapter\s+\d+.*"
    r"|(phase|stage|section|part|unit)\s+\d+.*"
    r"|\d+(\.\d+)*\.?\s+[A-Z][^.]{0,80}$"
    r"|[A-Z][A-Za-z\s,&/'\-]{3,70}:\s*$"
    r"|[A-Z][A-Z\s]{5,60}$"
    r")",
    re.IGNORECASE,
)


def _looks_like_heading(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 100:
        return False
    return bool(HEADING_PATTERN.match(line))


def _ocr_page(pdf_path: str, page_number: int) -> str:
    """Render a single page as an image and run Tesseract on it. Only
    called for pages that failed native extraction — keeps OCR cost
    limited to genuinely scanned pages, not the whole document by default."""
    try:
        kwargs = {"first_page": page_number, "last_page": page_number, "dpi": 300}
        if POPPLER_PATH:
            kwargs["poppler_path"] = POPPLER_PATH
        images = convert_from_path(pdf_path, **kwargs)
        if not images:
            return ""
        return pytesseract.image_to_string(images[0])
    except Exception as e:
        # OCR failing shouldn't crash the whole parse — just return empty
        # for this page and let the rest of the document still work.
        print(f"OCR failed for page {page_number}: {e}")
        return ""


def parse_pdf(file_path: str, force_ocr: bool = False) -> dict:
    """
    force_ocr: set True when the caller already knows this is a scanned
    document (e.g. from a user's "document nature" hint per FAQ guidance),
    to skip the native-extraction-then-check step and go straight to OCR.
    """
    sections = []
    tables = []
    images_or_figures = []
    full_text_parts = []
    ocr_pages_used = []
    current_section = {"heading": "Introduction", "level": 1, "text": ""}

    with pdfplumber.open(file_path) as pdf:
        page_count = len(pdf.pages)
        for page_num, page in enumerate(pdf.pages, start=1):
            text = "" if force_ocr else (page.extract_text() or "")

            if len(text.strip()) < MIN_CHARS_BEFORE_OCR_FALLBACK:
                ocr_text = _ocr_page(file_path, page_num)
                if len(ocr_text.strip()) > len(text.strip()):
                    text = ocr_text
                    ocr_pages_used.append(page_num)

            full_text_parts.append(text)

            for line in text.split("\n"):
                if _looks_like_heading(line):
                    if current_section["text"].strip():
                        sections.append(current_section)
                    current_section = {"heading": line.strip(), "level": 1, "text": ""}
                else:
                    current_section["text"] += line + "\n"

            for tbl in page.extract_tables():
                if tbl:
                    tables.append({"page": page_num, "rows": tbl})

            if page.images:
                images_or_figures.append({"page": page_num, "caption": None, "count": len(page.images)})

        if current_section["text"].strip():
            sections.append(current_section)

    raw_text = "\n".join(full_text_parts)
    return {
        "raw_text": raw_text,
        "sections": sections if sections else [{"heading": "Full Document", "level": 1, "text": raw_text}],
        "tables": tables,
        "images_or_figures": images_or_figures,
        "metadata": {
            "page_count": page_count,
            "word_count": len(raw_text.split()),
            "source_format": "pdf",
            "ocr_pages_used": ocr_pages_used,   # transparency: which pages needed OCR
        },
    }