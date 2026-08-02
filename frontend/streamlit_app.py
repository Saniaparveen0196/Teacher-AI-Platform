# frontend/streamlit_app.py
"""
Streamlit frontend for the Teacher AI Platform.
Talks to the FastAPI backend over HTTP — polls /jobs/{id}/result rather than
using SSE, since Streamlit doesn't have native SSE support; polling every
1-2s is simple and sufficient for this use case.
"""
import os
import time
import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Teacher AI Platform", layout="wide")
st.title("📚 Teacher Knowledge Package Generator")
st.caption("Upload a document, get a complete classroom-ready teaching package.")

if "job_id" not in st.session_state:
    st.session_state.job_id = None
if "tkp" not in st.session_state:
    st.session_state.tkp = None

# ---------- Upload form ----------

with st.form("upload_form"):
    uploaded_file = st.file_uploader("Upload document", type=["pdf", "docx", "pptx", "txt", "md"])
    col1, col2 = st.columns(2)
    with col1:
        target_periods = st.number_input("Target periods", min_value=1, max_value=10, value=5)
    with col2:
        period_duration = st.number_input("Period duration (min)", min_value=10, max_value=90, value=40)
    submitted = st.form_submit_button("Generate Teacher Knowledge Package")

if submitted and uploaded_file is not None:
    with st.spinner("Starting pipeline..."):
        response = requests.post(
            f"{BACKEND_URL}/jobs",
            files={"file": (uploaded_file.name, uploaded_file.getvalue())},
            data={"target_periods": target_periods, "period_duration_minutes": period_duration},
        )
    if response.status_code == 200:
        st.session_state.job_id = response.json()["job_id"]
        st.session_state.tkp = None
    else:
        st.error(f"Upload failed: {response.text}")

# ---------- Progress polling ----------

if st.session_state.job_id and st.session_state.tkp is None:
    progress_bar = st.progress(0, text="Waiting for pipeline...")
    job_id = st.session_state.job_id

    while True:
        result_resp = requests.get(f"{BACKEND_URL}/jobs/{job_id}/result")
        if result_resp.status_code == 200:
            st.session_state.tkp = result_resp.json()
            progress_bar.progress(100, text="Done!")
            break
        elif result_resp.status_code == 202:
            time.sleep(2)
            continue
        else:
            st.error(f"Pipeline failed: {result_resp.text}")
            break

    st.rerun()

# ---------- Results display ----------

if st.session_state.tkp:
    tkp = st.session_state.tkp
    st.success(f"Generated: **{tkp['classification']['topic']}** "
               f"({tkp['classification']['subject']}, {tkp['classification']['grade_level']})")

    val = tkp["validation_report"]
    status_icon = "✅" if val["passed"] else "⚠️"
    st.info(f"{status_icon} Validation: {val['objectives_coverage_pct']}% objective coverage, "
            f"{len(val['issues'])} issue(s) flagged")

    # PDF downloads
    st.subheader("Downloads")
    pdf_resp = requests.get(f"{BACKEND_URL}/jobs/{st.session_state.job_id}/pdfs")
    if pdf_resp.status_code == 200:
        urls = pdf_resp.json()
        col1, col2, col3 = st.columns(3)
        for col, (label, key) in zip(
            [col1, col2, col3],
            [("Lesson Plans", "lesson_plans_url"), ("Teacher Guide", "teacher_guide_url"),
             ("Assessment Book", "assessment_book_url")]
        ):
            with col:
                pdf_bytes = requests.get(f"{BACKEND_URL}{urls[key]}").content
                st.download_button(f"📄 {label}", pdf_bytes, file_name=f"{key.replace('_url', '')}.pdf")

    st.subheader("Full Package")
    tabs = st.tabs(["Classification", "Knowledge", "Teaching Plan", "Classroom Content",
                     "Activities", "Assessments", "Learning Gaps", "Validation"])

    with tabs[0]:
        st.json(tkp["classification"])

    with tabs[1]:
        k = tkp["knowledge"]
        st.write("**Learning Objectives**")
        for o in k["learning_objectives"]:
            st.write(f"- {o}")
        st.write("**Concepts**")
        for c in k["concepts"]:
            st.write(f"- **{c['name']}**: {c['explanation']}")
        if k["formulae"]:
            st.write("**Formulae**")
            for f in k["formulae"]:
                st.write(f"- **{f['name']}**: {f['expression']} — {f['explanation']}")

    with tabs[2]:
        for period in tkp["teaching_plan"]["periods"]:
            with st.expander(f"Period {period['period_number']}: {period['title']} ({period['duration_minutes']} min)"):
                st.write("**Objectives:**", ", ".join(period["learning_objectives"]))
                st.write("**Rationale:**", period["sequencing_rationale"])

    with tabs[3]:
        for period in tkp["classroom_content"]["periods"]:
            with st.expander(f"Period {period['period_number']}"):
                st.write("**Entry Ticket:**", period["entry_ticket"])
                st.write("**Teacher Script:**", period["teacher_script"])
                st.write("**Blackboard Notes:**", period["blackboard_notes"])
                st.write("**Mentor Moment:**", period["mentor_moment"])

    with tabs[4]:
        for period in tkp["activity_plan"]["periods"]:
            with st.expander(f"Period {period['period_number']}"):
                for act in period["activities"]:
                    st.write(f"**{act['name']}** ({act['activity_type']}, {act['duration_minutes']} min)")
                    st.write(act["teacher_instructions"])

    with tabs[5]:
        for period in tkp["assessment_plan"]["periods"]:
            with st.expander(f"Period {period['period_number']}"):
                st.write(f"MCQs: {len(period['mcqs'])} | Short: {len(period['short_answer'])} | "
                         f"Long: {len(period['long_answer'])} | Numerical: {len(period['numerical_problems'])}")

    with tabs[6]:
        for period in tkp["gap_analysis"]["periods"]:
            with st.expander(f"Period {period['period_number']}"):
                for gap in period["gaps"]:
                    st.write(f"**[{gap['severity']}] {gap['misconception']}**")
                    st.write(f"Remedy: {gap['remedial_action']}")

    with tabs[7]:
        st.write(f"**Passed:** {val['passed']} | **Coverage:** {val['objectives_coverage_pct']}%")
        for issue in val["issues"]:
            st.write(f"**[{issue['severity']}] {issue['category']}** ({issue.get('location', 'N/A')})")
            st.write(issue["description"])

    if st.button("Start Over"):
        st.session_state.job_id = None
        st.session_state.tkp = None
        st.rerun()