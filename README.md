# Teacher AI Platform

An AI-powered system that converts raw educational documents (PDF, DOCX, PPTX, TXT) into a structured, classroom-ready **Teacher Knowledge Package (TKP)** — complete lesson plans, activities, assessments, and learning gap analysis, generated through a 10-stage AI pipeline.

**Live demo:** https://teacher-ai-platform-frontend.onrender.com
**Backend API:** https://teacher-ai-platform-9mg3.onrender.com
**Repository:** https://github.com/Saniaparveen0196/Teacher-AI-Platform

---

## What it does

Upload a document (e.g. an NCERT textbook chapter), and the system:
1. Parses it while preserving structure (headings, tables, figures)
2. Classifies it (subject, grade, difficulty, topic)
3. Extracts learning objectives, concepts, definitions, formulae, misconceptions
4. Plans a multi-period teaching sequence
5. Generates full classroom content, activities, and assessments per period
6. Identifies likely student misconceptions with remediation strategies
7. Validates the output for consistency and grounding
8. Packages everything into `TeacherKnowledgePackage.json` plus downloadable PDFs (Lesson Plans, Teacher Guide, Assessment Book)

---

## Architecture
### Pipeline stages

| # | Stage | What it does |
|---|-------|---------------|
| 1 | Document Intelligence | Format-specific parsers (PDF/DOCX/PPTX/TXT) → one common structural shape. Includes OCR fallback (Tesseract + PyMuPDF) for scanned PDFs. |
| 2 | Educational Classification | Subject, grade, difficulty, topic, category, language |
| 3 | Knowledge Extraction | Learning objectives, prerequisites, concepts, definitions, formulae, examples, misconceptions |
| 4 | Teaching Planner | Multi-period sequence; period count adapts to content volume, not fixed at 5 |
| 5 | Classroom Content Generation | Entry tickets, teacher scripts, blackboard notes, checkpoint questions, exit tickets, homework, mentor moments |
| 6 | Activity Generation | Elaborates Stage 5's activity ideas into full specs (materials, instructions, success criteria) |
| 7 | Assessment Generation | MCQs, short/long answer, numerical problems (only when subject-appropriate), with rubrics |
| 8 | Learning Gap Analysis | Diagnostic questions, severity ratings, remedial actions per period |
| 9 | Validation | Hybrid deterministic + LLM checks (see below) |
| 10 | Publishing | Assembles `TeacherKnowledgePackage.json`, exports 3 PDFs, streams progress via SSE |

---

## Orchestration approach: custom pipeline, not LangChain

This system deliberately does **not** use LangChain, LlamaIndex, or a similar agent framework. Reasoning:

- **Fine-grained token budget control.** Running on a free-tier LLM API (Groq) with strict per-minute and per-day token limits, every stage needed a hand-tuned `max_output_tokens` and input-truncation strategy. A framework's abstractions would obscure exactly where tokens are being spent.
- **Per-stage caching.** A custom disk cache (`app/cache.py`), keyed on exact prompt content, means re-running any stage during development costs zero tokens on a cache hit. This was essential for iterating quickly within free-tier rate limits, and doubles as a "Performance Optimization" bonus feature.
- **Explicit schema validation at every boundary.** Every stage's raw LLM output is normalized (handling field-name synonyms an LLM might use) and validated against a Pydantic schema before being passed downstream — catching malformed output immediately rather than propagating errors silently through a framework's internal state.
- **Multi-agent separation.** Each stage is its own module with its own system prompt, own schema, and a single clear responsibility — functionally a multi-agent architecture, just implemented directly rather than through a framework's agent abstraction.

The tradeoff: more code written by hand (prompt templates, retry logic, normalization) versus what a framework would provide out of the box. Given the free-tier constraints this project operates under, that tradeoff was worth it.

---

## Engineering highlights

- **Streaming progress API**: the orchestrator (`app/orchestrator.py`) is a Python generator; each `yield` is one progress event (`{"stage": ..., "progress": N}`), consumed via Server-Sent Events in FastAPI (`/jobs/{id}/stream`).
- **Hybrid validation (Stage 9)**: cheap deterministic checks (objective coverage, period-count consistency, schema adherence) run in plain Python with zero LLM calls; only genuinely judgment-requiring checks (hallucination detection, pedagogical consistency) use an LLM call. Avoids reaching for the LLM as a hammer for everything.
- **Graceful degradation on unparseable input**: if Stage 1 extracts near-zero text (e.g. an unrecoverable scanned/corrupted PDF), the pipeline stops immediately with a clear error rather than silently generating a plausible-looking but content-free lesson plan.
- **Retry-safe LLM calls**: every call is wrapped with `tenacity` (exponential backoff, 3 attempts), handling transient rate-limit and JSON-parse failures automatically.
- **Optional curriculum alignment & multilingual output**: every generation stage accepts optional `curriculum_board` (CBSE/ICSE/Common Core) and `target_language` parameters, appended as additional instructions to each stage's prompt — adapting pacing/terminology or output language without any structural pipeline changes.

---

## Known limitations

- **OCR reliability**: scanned-PDF support (Tesseract + PyMuPDF rendering) was implemented and tested, but during development one real-world scanned PDF was found to have corrupted internal image streams that neither Poppler nor MuPDF could render — a file-level issue, not a pipeline bug. Recommend testing OCR against a variety of real scanned files before production use.
- **Stage 9 hallucination checks currently review `classroom_content` only**, not `assessment_plan`. Extending the review to spot-check assessment answer-key correctness is a natural next step.
- **Streamlit polls rather than streams**: the backend fully supports SSE (`/jobs/{id}/stream`), but Streamlit has no native SSE client, so the frontend polls `/jobs/{id}/result` with incremental progress feedback instead of consuming the live stream. A dedicated frontend (React + EventSource) would give smoother live progress.
- **Generation time**: a 5-period document makes ~20-24 sequential LLM calls (content/activities/assessments/gaps per period), taking roughly 2-4 minutes on the free-tier API used for this project.

---

## Setup — running locally

### Prerequisites
- Python 3.10+
- A free Groq API key: https://console.groq.com/keys
- (Optional, for scanned-PDF OCR) Tesseract OCR and Poppler installed locally

### Steps

```bash
git clone [YOUR_GITHUB_URL_HERE]
cd teacher-ai-platform
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in:
Run the backend:
```bash
uvicorn app.main:app --reload --port 8000
```

Run the frontend (separate terminal):
```bash
streamlit run frontend/streamlit_app.py
```

Set `BACKEND_URL` as an environment variable for the frontend if the backend isn't on `localhost:8000`.

---

## Sample outputs

Two sample `TeacherKnowledgePackage.json` files are in `/samples`, demonstrating cross-subject adaptability as required:
- `sample_tkp_stem.json` — Chemistry, "Structure of the Atom" (formulae, numerical assessment problems present)
- `sample_tkp_humanities.json` — History, "The French Revolution" (no formulae; assessments favor analytical short/long-answer questions)

---

## Tech stack

- **Backend**: FastAPI, Pydantic, `sse-starlette`
- **LLM**: Groq (`llama-3.3-70b-versatile`) — free-tier, provider-agnostic via a single gateway module (`app/llm_client.py`), swappable to any provider by editing one file
- **Parsing**: `pdfplumber`, `python-docx`, `python-pptx`, with OCR fallback via `pytesseract` + PyMuPDF
- **PDF generation**: `reportlab`
- **Frontend**: Streamlit
- **Caching**: custom disk cache keyed on prompt content
- **Retry/resilience**: `tenacity`
