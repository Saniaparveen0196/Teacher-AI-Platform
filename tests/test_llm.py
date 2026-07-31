from dotenv import load_dotenv
load_dotenv()
from app.llm_client import generate_json

result = generate_json(
    system_prompt="You are a helpful assistant. Always respond with valid JSON only.",
    user_prompt='Return JSON: {"greeting": "<a friendly hello>", "number": <any int>}',
)
print(result)
