# app/cache.py
"""
Disk-backed cache for LLM calls, keyed by a hash of the exact prompt content.
Purely a development/cost-saving optimization: identical (system_prompt,
user_prompt, temperature) always produces a cache hit, so re-running earlier
stages while testing a later one costs zero tokens. Doubles as the
"performance optimization / caching" bonus point for the assignment.
"""
import os
import json
import hashlib

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "storage", "llm_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

CACHE_ENABLED = os.environ.get("LLM_CACHE_ENABLED", "true").lower() == "true"


def _cache_key(system_prompt: str, user_prompt: str, temperature: float) -> str:
    raw = f"{system_prompt}|||{user_prompt}|||{temperature}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_cached(system_prompt: str, user_prompt: str, temperature: float):
    if not CACHE_ENABLED:
        return None
    key = _cache_key(system_prompt, user_prompt, temperature)
    path = os.path.join(CACHE_DIR, f"{key}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def set_cached(system_prompt: str, user_prompt: str, temperature: float, result: dict):
    if not CACHE_ENABLED:
        return
    key = _cache_key(system_prompt, user_prompt, temperature)
    path = os.path.join(CACHE_DIR, f"{key}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f)