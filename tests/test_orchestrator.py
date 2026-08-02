# tests/test_orchestrator.py
from dotenv import load_dotenv
load_dotenv()

import json
from app.orchestrator import run_pipeline
from tests.config import TEST_DOC_STEM

for event in run_pipeline(TEST_DOC_STEM, source_filename="atomic_structure.txt",
                           target_periods=5, period_duration_minutes=40):
    if "result" in event:
        print(f"\n[{event['stage']}] {event['progress']}% — DONE")
        # Save the full TKP so Part B (PDF export) can use it without re-running the pipeline
        with open("samples/sample_tkp_stem.json", "w", encoding="utf-8") as f:
            json.dump(event["result"], f, indent=2)
        print("Saved to samples/sample_tkp_stem.json")
    else:
        print(f"[{event['stage']}] {event['progress']}% — {event['message']}")