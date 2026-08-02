# app/job_store.py
import uuid
import threading

_jobs = {}
_lock = threading.Lock()


def create_job() -> str:
    job_id = str(uuid.uuid4())
    with _lock:
        _jobs[job_id] = {
            "status": "pending",
            "events": [],
            "result": None,
            "error": None,
        }
    return job_id


def append_event(job_id: str, event: dict):
    with _lock:
        _jobs[job_id]["events"].append(event)
        if event.get("progress") == 100 and "result" in event:
            _jobs[job_id]["result"] = event["result"]
            _jobs[job_id]["status"] = "done"


def set_running(job_id: str):
    with _lock:
        _jobs[job_id]["status"] = "running"


def set_error(job_id: str, error_message: str):
    with _lock:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = error_message


def get_job(job_id: str) -> dict:
    with _lock:
        return dict(_jobs.get(job_id, {}))


def get_new_events(job_id: str, since_index: int):
    with _lock:
        events = _jobs.get(job_id, {}).get("events", [])
        return events[since_index:], len(events)