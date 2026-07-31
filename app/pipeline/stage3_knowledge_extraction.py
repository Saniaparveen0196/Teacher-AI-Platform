# app/pipeline/stage3_knowledge_extraction.py
"""
Stage 3 — Knowledge Extraction.
The most structurally important stage in the pipeline: every stage from
Stage 4 onward is built entirely on top of this output.

Input size and output token budget are both capped to stay under Groq's
free-tier TPM limit (12,000 tokens/minute on llama-3.1-8b-instant).
"""
from app.llm_client import generate_json
from app.models import KnowledgeExtraction
from app.utils import truncate_text

SYSTEM_PROMPT = """You are an expert curriculum designer and subject-matter
analyst. Given the full text of an educational document and its classification
metadata, extract a complete structured knowledge representation.

CRITICAL RULE: Not every document has every category. A Humanities text will
likely have an empty formulae list. When a category genuinely does not
apply, return an EMPTY LIST for it — never omit the key, never invent
content to fill it, never fabricate anything not supported by the document.

Respond ONLY with a JSON object matching EXACTLY this structure and these
field names (do not rename, add, or omit any field):

{
  "learning_objectives": ["string", ...],
  "prerequisites": ["string", ...],
  "concepts": [{"name": "string", "explanation": "string"}, ...],
  "definitions": [{"term": "string", "definition": "string"}, ...],
  "formulae": [{"name": "string", "expression": "string", "explanation": "string"}, ...],
  "keywords": ["string", ...],
  "examples": [{"description": "string", "relates_to_concept": "string or null"}, ...],
  "applications": ["string", ...],
  "common_misconceptions": [{"misconception": "string", "correction": "string"}, ...]
}

Every object in every list MUST use exactly these field names:
- concepts → "name", "explanation"
- definitions → "term", "definition"
- formulae → "name", "expression", "explanation"
- examples → "description", "relates_to_concept"
- common_misconceptions → "misconception", "correction"
"""


def _build_extraction_text(parsed_doc: dict, max_chars: int = 9000) -> str:
    """Near-full document text, capped to stay within the LLM's TPM budget."""
    return truncate_text(parsed_doc["raw_text"], max_chars)


# Maps common LLM field-name synonyms -> our canonical schema field names.
# Cheap insurance against structured-output drift.
_FIELD_ALIASES = {
    "examples": {"example": "description", "text": "description", "concept": "relates_to_concept"},
    "common_misconceptions": {
        "correct_understanding": "correction", "clarification": "correction",
        "fix": "correction", "truth": "correction",
    },
    "concepts": {"concept": "name", "description": "explanation"},
    "definitions": {"word": "term", "meaning": "definition"},
    "formulae": {"formula": "expression", "description": "explanation"},
}


def _normalize_list_field(items: list, field_name: str) -> list:
    aliases = _FIELD_ALIASES.get(field_name)
    if not aliases or not items:
        return items
    normalized = []
    for item in items:
        if not isinstance(item, dict):
            normalized.append(item)
            continue
        fixed = dict(item)
        for wrong_key, correct_key in aliases.items():
            if wrong_key in fixed and correct_key not in fixed:
                fixed[correct_key] = fixed.pop(wrong_key)
        normalized.append(fixed)
    return normalized


def _normalize_result(result: dict) -> dict:
    for field_name in ["concepts", "definitions", "formulae", "examples", "common_misconceptions"]:
        if field_name in result and isinstance(result[field_name], list):
            result[field_name] = _normalize_list_field(result[field_name], field_name)
    return result


def extract_knowledge(parsed_doc: dict, classification: dict) -> dict:
    doc_text = _build_extraction_text(parsed_doc)

    user_prompt = f"""Document metadata:
- Subject: {classification['subject']}
- Grade level: {classification['grade_level']}
- Difficulty: {classification['difficulty']}
- Topic: {classification['topic']}
- Category: {classification['category']}

Full document text:
{doc_text}

Extract the complete structured knowledge representation as specified."""

    result = generate_json(SYSTEM_PROMPT, user_prompt, temperature=0.3,  max_output_tokens=3072)
    result = _normalize_result(result)
    validated = KnowledgeExtraction(**result)
    return validated.model_dump()