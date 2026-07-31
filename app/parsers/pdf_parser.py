# app/parsers/pdf_parser.py
import re
import pdfplumber

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


def parse_pdf(file_path: str) -> dict:
    sections = []
    tables = []
    images_or_figures = []
    full_text_parts = []
    current_section = {"heading": "Introduction", "level": 1, "text": ""}

    with pdfplumber.open(file_path) as pdf:
        page_count = len(pdf.pages)
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
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
        },
    }