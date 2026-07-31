# app/parsers/txt_parser.py
"""
Stage 1 — Document Intelligence: plain text / markdown parser.
Simplest of the four — no structural metadata to lean on, so we detect
markdown-style headers if present, else fall back to a short-line heuristic.
"""
import re

MD_HEADER = re.compile(r"^(#{1,6})\s+(.*)")


def _looks_like_plain_heading(line: str, next_line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 80:
        return False
    if line.endswith((".", ",", ";")):
        return False
    # Heuristic: short standalone line followed by a blank line looks like a heading
    return next_line.strip() == ""


def parse_txt(file_path: str) -> dict:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.read().split("\n")

    sections = []
    current_section = {"heading": "Introduction", "level": 1, "text": ""}

    for idx, line in enumerate(lines):
        stripped = line.strip()
        next_line = lines[idx + 1] if idx + 1 < len(lines) else ""

        md_match = MD_HEADER.match(stripped)
        if md_match:
            if current_section["text"].strip():
                sections.append(current_section)
            level = len(md_match.group(1))
            current_section = {"heading": md_match.group(2).strip(), "level": level, "text": ""}
        elif _looks_like_plain_heading(stripped, next_line):
            if current_section["text"].strip():
                sections.append(current_section)
            current_section = {"heading": stripped, "level": 1, "text": ""}
        else:
            current_section["text"] += line + "\n"

    if current_section["text"].strip():
        sections.append(current_section)

    raw_text = "\n".join(lines)
    return {
        "raw_text": raw_text,
        "sections": sections if sections else [{"heading": "Full Document", "level": 1, "text": raw_text}],
        "tables": [],
        "images_or_figures": [],
        "metadata": {
            "page_count": None,
            "word_count": len(raw_text.split()),
            "source_format": "txt",
        },
    }