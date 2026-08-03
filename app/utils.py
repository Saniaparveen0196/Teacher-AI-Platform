# app/utils.py
"""
Shared helpers used across pipeline stages.
"""

def truncate_text(text: str, max_chars: int) -> str:
    """Rough token-safe truncation. ~4 chars/token is a safe approximation
    for English text, so this indirectly keeps us under Groq's TPM limits."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[...truncated for length...]"


def build_context_suffix(curriculum_board: str = None, target_language: str = None) -> str:
    """
    Builds an optional instruction suffix appended to generation prompts,
    for curriculum alignment (CBSE/ICSE/Common Core/etc.) and multilingual
    output. Returns an empty string if neither is set, so existing prompts
    behave identically when these features aren't used.
    """
    parts = []
    if curriculum_board:
        parts.append(
            f"Align this content with the {curriculum_board} curriculum framework's "
            f"typical pacing, terminology, and pedagogical conventions where applicable."
        )
    if target_language:
        parts.append(f"Generate ALL content in {target_language}, including questions, "
                      f"instructions, and explanations — do not mix languages.")
    if not parts:
        return ""
    return "\n\nIMPORTANT ADDITIONAL REQUIREMENTS:\n" + "\n".join(f"- {p}" for p in parts)