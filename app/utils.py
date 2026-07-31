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