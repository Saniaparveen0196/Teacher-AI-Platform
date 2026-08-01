# test_cache.py
from dotenv import load_dotenv
load_dotenv()
from app.llm_client import generate_json

r1 = generate_json("You are helpful. Respond in JSON only.", 'Return {"x": 1}', temperature=0.2)
print("First call:", r1)
r2 = generate_json("You are helpful. Respond in JSON only.", 'Return {"x": 1}', temperature=0.2)
print("Second call:", r2)