# frontend/streamlit_app.py
"""
Streamlit frontend for the Teacher AI Platform.
Talks to the FastAPI backend over HTTP — polls /jobs/{id}/result rather than
using SSE, since Streamlit doesn't have native SSE support; polling with
incremental progress feedback is simple and sufficient for this use case.
"""
import os
import time
import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Teacher AI Platform", page_icon="📚", layout="wide")

# ---------- Light styling polish ----------
st.markdown("""
<style>
    .main > div { padding-top: 1.5rem; }
    div[data-testid="stMetricValue"] { font-size: 1.4rem; }
    .stTabs [data-baseweb="tab"] { font-weight: 500; }
    div.stButton > button, div.stDownloadButton > button { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

st.title("📚 Teacher Knowledge Package Generator")
st.caption("Upload a raw educational document — get back a complete, classroom-ready teaching package.")

if "job_id" not in st.session_state:
    st.session_state.job_id = None
if "tkp" not in st.session_state:
    st.session_state.tkp = None
if "error" not in st.session_state:
    st.session_state.error = None

# ---------- Upload form ----------

# frontend/streamlit_app.py — REPLACE the upload form block with this

with st.form("upload_form"):
    uploaded_file = st.file_uploader(
        "Upload document", type=["pdf", "docx", "pptx", "txt", "md"],
        help="PDF, DOCX, PPTX, or plain text. Scanned PDFs use OCR fallback automatically."
    )
    col1, col2 = st.columns(2)
    with col1:
        target_periods = st.number_input("Target periods", min_value=1, max_value=10, value=5,
                                          help="The AI may adjust this based on content volume.")
    with col2:
        period_duration = st.number_input("Period duration (min)", min_value=10, max_value=90, value=40)

    col3, col4 = st.columns(2)
    with col3:
        curriculum_board = st.selectbox(
            "Curriculum alignment (optional)",
            ["None", "CBSE", "ICSE", "Common Core", "State Board"],
        )
    with col4:
        target_language = st.selectbox(
            "Output language (optional)",
            ["Same as source document", "English", "Hindi", "Spanish", "French"],
        )

    submitted = st.form_submit_button("🚀 Generate Teacher Knowledge Package", use_container_width=True)

if submitted and uploaded_file is not None:
    with st.spinner("Uploading and starting pipeline..."):
        response = requests.post(
            f"{BACKEND_URL}/jobs",
            files={"file": (uploaded_file.name, uploaded_file.getvalue())},
            data={
                "target_periods": target_periods,
                "period_duration_minutes": period_duration,
                "curriculum_board": None if curriculum_board == "None" else curriculum_board,
                "target_language": None if target_language == "Same as source document" else target_language,
            },
        )
    if response.status_code == 200:
        st.session_state.job_id = response.json()["job_id"]
        st.session_state.tkp = None
        st.session_state.error = None
        st.rerun()
    else:
        st.error(f"Upload failed: {response.text}")

# ---------- Progress polling ----------

_STAGE_LABELS = [
    "Parsing document", "Classifying content", "Extracting knowledge",
    "Planning periods", "Generating classroom content", "Designing activities",
    "Building assessments", "Analyzing learning gaps", "Validating output", "Packaging results",
]

if st.session_state.job_id and st.session_state.tkp is None and st.session_state.error is None:
    job_id = st.session_state.job_id
    st.info("⏳ Generation typically takes **2–4 minutes** for a 5-period document — each period's "
            "content, activities, assessments, and gap analysis are generated as separate AI calls.")
    progress_bar = st.progress(0, text="Starting...")
    stage_placeholder = st.empty()

    poll_count = 0
    while True:
        result_resp = requests.get(f"{BACKEND_URL}/jobs/{job_id}/result")
        if result_resp.status_code == 200:
            st.session_state.tkp = result_resp.json()
            progress_bar.progress(100, text="Done!")
            break
        elif result_resp.status_code == 202:
            poll_count += 1
            # Approximate progress since /result doesn't expose live per-stage
            # detail — gives visible movement so the wait doesn't look frozen.
            pct = min(5 + poll_count * 3, 95)
            stage_idx = min(poll_count // 4, len(_STAGE_LABELS) - 1)
            progress_bar.progress(pct, text=f"{_STAGE_LABELS[stage_idx]}...")
            time.sleep(3)
        else:
            st.session_state.error = result_resp.text
            break
    st.rerun()

if st.session_state.error:
    st.error(f"⚠️ Generation failed: {st.session_state.error}")
    st.caption("Common cause: the document couldn't be read (scanned PDF with failed OCR, or a "
               "corrupted file). Try a different file, or a plain .txt/.docx version.")
    if st.button("Try another file"):
        st.session_state.job_id = None
        st.session_state.error = None
        st.rerun()

# ---------- Results display ----------

if st.session_state.tkp:
    tkp = st.session_state.tkp
    cls = tkp["classification"]
    val = tkp["validation_report"]

    st.success(f"✅ Generated: **{cls['topic']}**")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Subject", cls["subject"])
    m2.metric("Grade Level", cls["grade_level"])
    m3.metric("Periods", tkp["teaching_plan"]["total_periods"])
    m4.metric("Objective Coverage", f"{val['objectives_coverage_pct']}%",
              delta="✅ Passed" if val["passed"] else "⚠️ Issues found", delta_color="off")

    st.divider()

    # PDF downloads
    st.subheader("📥 Downloads")
    pdf_resp = requests.get(f"{BACKEND_URL}/jobs/{st.session_state.job_id}/pdfs")
    if pdf_resp.status_code == 200:
        urls = pdf_resp.json()
        col1, col2, col3 = st.columns(3)
        for col, (label, key) in zip(
            [col1, col2, col3],
            [("📄 Lesson Plans", "lesson_plans_url"), ("📘 Teacher Guide", "teacher_guide_url"),
             ("📝 Assessment Book", "assessment_book_url")]
        ):
            with col:
                pdf_bytes = requests.get(f"{BACKEND_URL}{urls[key]}").content
                st.download_button(label, pdf_bytes, file_name=f"{key.replace('_url', '')}.pdf",
                                    use_container_width=True)

    st.divider()
    st.subheader("📦 Full Package")
    tabs = st.tabs(["🏷️ Classification", "🧠 Knowledge", "🗓️ Teaching Plan", "🎓 Classroom Content",
                     "🎯 Activities", "✍️ Assessments", "⚠️ Learning Gaps", "✅ Validation"])

    with tabs[0]:
        st.json(cls)

    with tabs[1]:
        k = tkp["knowledge"]
        st.markdown("**Learning Objectives**")
        for o in k["learning_objectives"]:
            st.write(f"- {o}")
        st.markdown("**Concepts**")
        for c in k["concepts"]:
            st.write(f"- **{c['name']}**: {c['explanation']}")
        if k["definitions"]:
            st.markdown("**Definitions**")
            for d in k["definitions"]:
                st.write(f"- **{d['term']}**: {d['definition']}")
        if k["formulae"]:
            st.markdown("**Formulae**")
            for f in k["formulae"]:
                st.write(f"- **{f['name']}**: `{f['expression']}` — {f['explanation']}")
        if k["common_misconceptions"]:
            st.markdown("**Common Misconceptions**")
            for m in k["common_misconceptions"]:
                st.write(f"- ❌ {m['misconception']} → ✅ {m['correction']}")

    with tabs[2]:
        for period in tkp["teaching_plan"]["periods"]:
            with st.expander(f"Period {period['period_number']}: {period['title']} ({period['duration_minutes']} min)"):
                st.write("**Objectives:**", ", ".join(period["learning_objectives"]))
                st.write("**Concepts covered:**", ", ".join(period["concepts_covered"]))
                st.caption(period["sequencing_rationale"])

    with tabs[3]:
        for period in tkp["classroom_content"]["periods"]:
            with st.expander(f"Period {period['period_number']}"):
                st.write("**Entry Ticket:**", period["entry_ticket"])
                st.write("**Teacher Script:**", period["teacher_script"])
                st.write("**Blackboard Notes:**", period["blackboard_notes"])
                st.write("**Exit Ticket:**", period["exit_ticket"])
                st.write("**Homework:**", period["homework"])
                st.info(f"💡 **Mentor Moment:** {period['mentor_moment']}")

    with tabs[4]:
        for period in tkp["activity_plan"]["periods"]:
            with st.expander(f"Period {period['period_number']} — {len(period['activities'])} activities"):
                for act in period["activities"]:
                    st.markdown(f"**{act['name']}** *({act['activity_type']}, {act['duration_minutes']} min)*")
                    st.write(f"Materials: {', '.join(act['materials_needed'])}")
                    st.write(act["teacher_instructions"])
                    st.caption(f"Success criteria: {act['success_criteria']}")
                    st.markdown("---")

    with tabs[5]:
        for period in tkp["assessment_plan"]["periods"]:
            with st.expander(f"Period {period['period_number']}"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("MCQs", len(period["mcqs"]))
                c2.metric("Short Answer", len(period["short_answer"]))
                c3.metric("Long Answer", len(period["long_answer"]))
                c4.metric("Numerical", len(period["numerical_problems"]))
                for mcq in period["mcqs"]:
                    st.write(f"**Q:** {mcq['question']}")
                    for j, opt in enumerate(mcq["options"]):
                        marker = chr(97 + j)
                        prefix = "✅" if opt == mcq["correct_answer"] else "◯"
                        st.write(f"&nbsp;&nbsp;{prefix} ({marker}) {opt}")

    with tabs[6]:
        for period in tkp["gap_analysis"]["periods"]:
            with st.expander(f"Period {period['period_number']} — {len(period['gaps'])} gap(s) identified"):
                for gap in period["gaps"]:
                    severity_icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(gap["severity"], "⚪")
                    st.markdown(f"{severity_icon} **{gap['misconception']}**")
                    st.write(f"*Diagnostic:* {gap['diagnostic_question']}")
                    st.write(f"*Remedy:* {gap['remedial_action']}")
                    st.markdown("---")

    with tabs[7]:
        status_icon = "✅" if val["passed"] else "⚠️"
        st.markdown(f"### {status_icon} Overall: {'Passed' if val['passed'] else 'Issues Found'}")
        st.metric("Objective Coverage", f"{val['objectives_coverage_pct']}%")
        if val["issues"]:
            for issue in val["issues"]:
                severity_icon = {"Critical": "🔴", "Warning": "🟡", "Info": "🔵"}.get(issue["severity"], "⚪")
                st.markdown(f"{severity_icon} **[{issue['category']}]** {issue.get('location', 'N/A')}")
                st.caption(issue["description"])
        else:
            st.write("No issues flagged.")

    st.divider()
    if st.button("🔄 Start Over"):
        st.session_state.job_id = None
        st.session_state.tkp = None
        st.session_state.error = None
        st.rerun()