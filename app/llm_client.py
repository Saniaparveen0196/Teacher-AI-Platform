# app/llm_client.py
"""
Central LLM gateway. No other file in this project imports the Groq/OpenAI
SDK directly — every pipeline stage calls generate_json() from here. This
means swapping providers later (Gemini/Claude/OpenAI) is a one-file change.
"""
import os
import json
import re
import logging
from dotenv import load_dotenv

from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from .cache import get_cached, set_cached
logger = logging.getLogger("tkp.llm")
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile"
)

_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


class LLMError(Exception):
    pass


class JSONParseError(LLMError):
    pass


def _extract_json(raw_text: str) -> dict:
    """LLMs often wrap JSON in ```json fences or add stray prose. Be forgiving."""
    text = raw_text.strip()
    text = re.sub(r"^```(json)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fallback: grab the largest {...} or [...] span in the text
    for open_c, close_c in [("{", "}"), ("[", "]")]:
        start, end = text.find(open_c), text.rfind(close_c)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                continue

    raise JSONParseError(f"Could not parse JSON. First 300 chars: {text[:300]}")




@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=15, max=60),
    retry=retry_if_exception_type((LLMError, ConnectionError, TimeoutError)),
    reraise=True,
)
def generate_json(system_prompt: str, user_prompt: str,
                   temperature: float = 0.4, max_output_tokens: int = 2048) -> dict:
    cached = get_cached(system_prompt, user_prompt, temperature)
    if cached is not None:
        logger.info("Cache hit — skipping LLM call")
        return cached

    if not _client:
        raise LLMError(
            "GROQ_API_KEY not set. Get a free key at "
            "https://console.groq.com/keys and put it in .env"
        )

    try:
        response = _client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=temperature,
            max_tokens=max_output_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as e:
        logger.warning(f"LLM call failed: {e}")
        raise LLMError(str(e)) from e

    raw_text = response.choices[0].message.content
    logger.info(f"LLM call ok, {len(raw_text)} chars")

    try:
        result = _extract_json(raw_text)
    except JSONParseError as e:
        logger.warning(f"JSON parse failed, retrying: {e}")
        raise

    set_cached(system_prompt, user_prompt, temperature, result)
    return result


def generate_text(system_prompt: str, user_prompt: str, temperature: float = 0.5) -> str:
    """Plain text generation (rare — most stages want structured JSON)."""
    if not _client:
        raise LLMError("GROQ_API_KEY not set.")
    response = _client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content