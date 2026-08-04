# app/pipeline/stage3_knowledge_extraction.py
"""
Stage 3 — Knowledge Extraction.
Uses RAG (TF-IDF retrieval over document chunks, see app/rag.py) to select
the most relevant passages for extraction, rather than blindly truncating
the document to fit the token budget. This means content relevant to the
document's actual topic is prioritized regardless of where it sits in the
document, and gives each extracted concept/definition a traceable
source_section for free (the chunk's originating heading).
"""
from app.llm_client import generate_json
from app.models import KnowledgeExtraction
from app.rag import build_index

SYSTEM_PROMPT = """You are an expert curriculum designer and subject-matter
analyst. Given retrieved passages from an educational document (each tagged
with its source section) and classification metadata, extract a complete
structured knowledge representation.

CRITICAL RULE: Not every document has every category. A Humanities text will
likely have an empty formulae list. When a category genuinely does not
apply, return an EMPTY LIST for it — never omit the key, never invent
content to fill it, never fabricate anything not supported by the provided
passages.

TRACEABILITY RULE: For each concept and definition, record which source
section (from the passage tags provided) it was drawn from, as
"source_section". If genuinely not attributable to one specific section,
use null.

Respond ONLY with a JSON object matching EXACTLY this structure and these
field names (do not rename, add, or omit any field):

{
  "learning_objectives": ["string", ...],
  "prerequisites": ["string", ...],
  "concepts": [{"name": "string", "explanation": "string", "source_section": "string or null"}, ...],
  "definitions": [{"term": "string", "definition": "string", "source_section": "string or null"}, ...],
  "formulae": [{"name": "string", "expression": "string", "explanation": "string"}, ...],
  "keywords": ["string", ...],
  "examples": [{"description": "string", "relates_to_concept": "string or null"}, ...],
  "applications": ["string", ...],
  "common_misconceptions": [{"misconception": "string", "correction": "string"}, ...]
}

Every object in every list MUST use exactly these field names:
- concepts → "name", "explanation", "source_section"
- definitions → "term", "definition", "source_section"
- formulae → "name", "expression", "explanation"
- examples → "description", "relates_to_concept"
- common_misconceptions → "misconception", "correction"
"""


_FIELD_ALIASES = {
    "examples": {"example": "description", "text": "description", "concept": "relates_to_concept"},
    "common_misconceptions": {
        "correct_understanding": "correction", "clarification": "correction",
        "fix": "correction", "truth": "correction",
    },
    "concepts": {"concept": "name", "description": "explanation", "section": "source_section",
                 "heading": "source_section"},
    "definitions": {"word": "term", "meaning": "definition", "section": "source_section",
                     "heading": "source_section"},
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
        if field_name in ("concepts", "definitions"):
            fixed.setdefault("source_section", None)
        normalized.append(fixed)
    return normalized


def _normalize_result(result: dict) -> dict:
    for field_name in ["concepts", "definitions", "formulae", "examples", "common_misconceptions"]:
        if field_name in result and isinstance(result[field_name], list):
            result[field_name] = _normalize_list_field(result[field_name], field_name)
    return result


def _build_retrieved_context(parsed_doc: dict, classification: dict, top_k: int = 8) -> str:
    """Builds the extraction input from retrieved chunks instead of blind
    truncation. Query is built from the document's own classification, since
    at this point we already know the topic/subject — retrieval selects the
    passages most relevant to that topic rather than just "the first N chars"."""
    index = build_index(parsed_doc)

    query = f"{classification['subject']} {classification['topic']} key concepts definitions formulae examples"
    retrieved = index.retrieve(query, top_k=top_k)

    if not retrieved:
        # Document too short to chunk meaningfully — just use everything
        return "\n\n".join(f"[Section: {s['heading']}]\n{s['text']}" for s in parsed_doc["sections"])

    return "\n\n".join(f"[Section: {c.section}]\n{c.text}" for c in retrieved)


def extract_knowledge(parsed_doc: dict, classification: dict) -> dict:
    retrieved_context = _build_retrieved_context(parsed_doc, classification)

    user_prompt = f"""Document metadata:
- Subject: {classification['subject']}
- Grade level: {classification['grade_level']}
- Difficulty: {classification['difficulty']}
- Topic: {classification['topic']}
- Category: {classification['category']}

Retrieved passages (most relevant sections for this topic, each tagged with
its source section):

{retrieved_context}

Extract the complete structured knowledge representation as specified,
tagging each concept and definition with the source_section it came from."""

    result = generate_json(SYSTEM_PROMPT, user_prompt, temperature=0.3, max_output_tokens=4096)
    result = _normalize_result(result)
    validated = KnowledgeExtraction(**result)
    return validated.model_dump()