# tests/test_orchestrator_humanities.py
from dotenv import load_dotenv
load_dotenv()

import json
from app.orchestrator import run_pipeline

for event in run_pipeline(
    "samples/french_revolution.txt",
    source_filename="french_revolution.txt",
    target_periods=5,
    period_duration_minutes=40,
):
    if "result" in event:
        print(f"\n[{event['stage']}] {event['progress']}% — DONE")
        with open("samples/sample_tkp_humanities.json", "w", encoding="utf-8") as f:
            json.dump(event["result"], f, indent=2)
        print("Saved to samples/sample_tkp_humanities.json")
    elif "error" in event:
        print(f"ERROR: {event['error']}")
    else:
        print(f"[{event['stage']}] {event['progress']}% — {event['message']}")