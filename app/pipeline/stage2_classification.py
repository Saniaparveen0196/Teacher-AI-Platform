# app/pipeline/stage2_classification.py
"""
Stage 2 — Educational Classification.
Determines Subject, Grade, Difficulty, Topic, Chapter, Category, Language
from the parsed document. Only needs a representative excerpt, not the
full text — that's Stage 3's job.
"""
from app.llm_client import generate_json
from app.models import DocumentClassification

SYSTEM_PROMPT = """You are an expert educational content classifier with years of
experience across all subjects and grade levels, from STEM to Humanities to
Languages and Arts.

Given excerpts from an educational document, determine:
- subject: the academic subject (e.g. "Physics", "World History", "English Literature")
- grade_level: the target grade/level (e.g. "Grade 9", "Undergraduate", "K-5")
- difficulty: one of "Beginner", "Intermediate", "Advanced"
- topic: the specific topic covered (e.g. "Photosynthesis", "The French Revolution")
- chapter: the chapter/unit title if identifiable, else null
- category: broad category — "STEM", "Humanities", "Language", "Arts", "Social Science",
  or "Other"
- language: the language the document is written in (e.g. "English")
- confidence: your confidence in this classification, 0.0 to 1.0

Respond ONLY with a JSON object with exactly these keys: subject, grade_level,
difficulty, topic, chapter, category, language, confidence.

If a field is genuinely undeterminable from the excerpt, make your best
reasonable inference rather than leaving it blank — but lower the confidence
score accordingly. Never invent additional keys."""


def _build_excerpt(parsed_doc: dict, max_chars: int = 3000) -> str:
    """Headings + a text sample from each section, capped at max_chars total."""
    parts = []
    total_len = 0
    for section in parsed_doc["sections"]:
        heading = section["heading"]
        sample = section["text"][:300].strip()
        chunk = f"## {heading}\n{sample}\n"
        if total_len + len(chunk) > max_chars:
            remaining = max_chars - total_len
            if remaining > 50:
                parts.append(chunk[:remaining])
            break
        parts.append(chunk)
        total_len += len(chunk)
    return "\n".join(parts)


def classify_document(parsed_doc: dict) -> dict:
    excerpt = _build_excerpt(parsed_doc)
    user_prompt = f"""Classify this educational document based on the following excerpt
(headings + text samples from each section):

{excerpt}

Respond with the JSON object as specified."""

    result = generate_json(SYSTEM_PROMPT, user_prompt, temperature=0.2, max_output_tokens=512)
    validated = DocumentClassification(**result)
    return validated.model_dump()