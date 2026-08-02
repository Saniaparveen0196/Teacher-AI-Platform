# app/main.py
import os
import shutil
import threading
import asyncio
import json

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse

from app.orchestrator import run_pipeline
from app.pdf_export import export_all_pdfs
from app.job_store import (
    create_job, append_event, set_running, set_error, get_job, get_new_events
)

app = FastAPI(title="Teacher AI Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "storage", "uploads")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "storage", "outputs")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _run_job_in_background(job_id, file_path, source_filename, target_periods, period_duration_minutes):
    set_running(job_id)
    try:
        for event in run_pipeline(file_path, source_filename, target_periods, period_duration_minutes):
            append_event(job_id, event)
    except Exception as e:
        set_error(job_id, str(e))


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/jobs")
async def create_pipeline_job(
    file: UploadFile = File(...),
    target_periods: int = Form(5),
    period_duration_minutes: int = Form(40),
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".pdf", ".docx", ".pptx", ".txt", ".md"):
        raise HTTPException(400, f"Unsupported file type: {ext}")

    job_id = create_job()
    saved_path = os.path.join(UPLOAD_DIR, f"{job_id}{ext}")
    with open(saved_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    thread = threading.Thread(
        target=_run_job_in_background,
        args=(job_id, saved_path, file.filename, target_periods, period_duration_minutes),
        daemon=True,
    )
    thread.start()
    return {"job_id": job_id}


@app.get("/jobs/{job_id}/stream")
async def stream_job_progress(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    async def event_generator():
        since_index = 0
        while True:
            job = get_job(job_id)
            if not job:
                break
            new_events, since_index = get_new_events(job_id, since_index)
            for event in new_events:
                slim_event = {k: v for k, v in event.items() if k != "result"}
                yield {"event": "progress", "data": json.dumps(slim_event)}
            if job["status"] in ("done", "error"):
                yield {"event": "complete", "data": json.dumps({"status": job["status"], "error": job.get("error")})}
                break
            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


@app.get("/jobs/{job_id}/result")
async def get_job_result(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job["status"] == "error":
        raise HTTPException(500, f"Pipeline failed: {job['error']}")
    if job["status"] != "done":
        raise HTTPException(202, "Job still running")
    return job["result"]


@app.get("/jobs/{job_id}/pdfs")
async def generate_and_list_pdfs(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job["status"] != "done":
        raise HTTPException(202, "Job still running")

    job_output_dir = os.path.join(OUTPUT_DIR, job_id)
    export_all_pdfs(job["result"], job_output_dir)
    return {
        "lesson_plans_url": f"/jobs/{job_id}/pdfs/lesson_plans",
        "teacher_guide_url": f"/jobs/{job_id}/pdfs/teacher_guide",
        "assessment_book_url": f"/jobs/{job_id}/pdfs/assessment_book",
    }


@app.get("/jobs/{job_id}/pdfs/{pdf_type}")
async def download_pdf(job_id: str, pdf_type: str):
    valid_types = {"lesson_plans", "teacher_guide", "assessment_book"}
    if pdf_type not in valid_types:
        raise HTTPException(400, f"pdf_type must be one of {valid_types}")
    pdf_path = os.path.join(OUTPUT_DIR, job_id, f"{pdf_type}.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(404, "PDF not generated yet")
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"{pdf_type}.pdf")