# app/pdf_export.py
"""
Stage 10 — Publishing: PDF export.
Generates three consumable PDFs from a TeacherKnowledgePackage dict:
Lesson Plans, Teacher Guide, Assessment Book. Uses reportlab's flowables
(Paragraph/Table/Spacer) rather than low-level canvas drawing, since teacher
scripts and model answers are long variable-length text that needs automatic
wrapping/pagination.
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, ListFlowable, ListItem
)

_styles = getSampleStyleSheet()
_styles.add(ParagraphStyle(name="H1Custom", fontSize=18, leading=22, spaceAfter=12, textColor=colors.HexColor("#1a1a2e")))
_styles.add(ParagraphStyle(name="H2Custom", fontSize=14, leading=18, spaceBefore=14, spaceAfter=8, textColor=colors.HexColor("#16213e")))
_styles.add(ParagraphStyle(name="H3Custom", fontSize=12, leading=15, spaceBefore=10, spaceAfter=6, textColor=colors.HexColor("#0f3460")))
_styles.add(ParagraphStyle(name="BodyCustom", fontSize=10, leading=14, spaceAfter=6))
_styles.add(ParagraphStyle(name="MetaCustom", fontSize=9, leading=12, textColor=colors.grey))
_styles.add(ParagraphStyle(name="OptionCustom", fontSize=10, leading=14, leftIndent=20, spaceAfter=3))


def _p(text: str, style: str = "BodyCustom"):
    """Escape and wrap text as a Paragraph flowable. Only escapes raw &/<atml:cite index=">, "
    doesn't inject HTML entities like &nbsp; — use reportlab's leftIndent
    for indentation instead, since &nbsp; gets double-escaped otherwise."""
    safe = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Re-enable the specific inline tags we intentionally use (<b>, <i>) after escaping
    safe = safe.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
    safe = safe.replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")
    return Paragraph(safe, _styles[style])


def _bullet_list(items: list):
    return ListFlowable(
        [ListItem(_p(item), leftIndent=10) for item in items],
        bulletType="bullet", start="•"
    )


def _build_doc(output_path: str, title: str, story: list):
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm,
    )
    doc.build(story)
    return output_path


# ---------- Lesson Plans PDF ----------

def export_lesson_plans_pdf(tkp: dict, output_path: str) -> str:
    story = [
        _p(f"Lesson Plans: {tkp['classification']['topic']}", "H1Custom"),
        _p(f"{tkp['classification']['subject']} | {tkp['classification']['grade_level']} | "
           f"{tkp['classification']['difficulty']}", "MetaCustom"),
        Spacer(1, 0.5 * cm),
    ]

    content_by_period = {p["period_number"]: p for p in tkp["classroom_content"]["periods"]}

    for period in tkp["teaching_plan"]["periods"]:
        content = content_by_period.get(period["period_number"])
        story.append(_p(f"Period {period['period_number']}: {period['title']} "
                         f"({period['duration_minutes']} min)", "H2Custom"))
        story.append(_p("Learning Objectives", "H3Custom"))
        story.append(_bullet_list(period["learning_objectives"]))

        if content:
            story.append(_p("Entry Ticket", "H3Custom"))
            story.append(_p(content["entry_ticket"]))
            story.append(_p("Teacher Script", "H3Custom"))
            story.append(_p(content["teacher_script"]))
            story.append(_p("Blackboard Notes", "H3Custom"))
            story.append(_p(content["blackboard_notes"]))
            story.append(_p("Checkpoint Questions", "H3Custom"))
            story.append(_bullet_list(content["checkpoint_questions"]))
            story.append(_p("Exit Ticket", "H3Custom"))
            story.append(_p(content["exit_ticket"]))
            story.append(_p("Homework", "H3Custom"))
            story.append(_p(content["homework"]))
            story.append(_p("Mentor Moment", "H3Custom"))
            story.append(_p(content["mentor_moment"]))

        story.append(PageBreak())

    if story and isinstance(story[-1], PageBreak):
        story.pop()  # avoid a trailing blank page

    return _build_doc(output_path, "Lesson Plans", story)


# ---------- Teacher Guide PDF ----------

def export_teacher_guide_pdf(tkp: dict, output_path: str) -> str:
    story = [
        _p(f"Teacher Guide: {tkp['classification']['topic']}", "H1Custom"),
        _p(f"{tkp['classification']['subject']} | {tkp['classification']['grade_level']}", "MetaCustom"),
        Spacer(1, 0.5 * cm),
    ]

    k = tkp["knowledge"]

    story.append(_p("Core Concepts", "H2Custom"))
    for c in k["concepts"]:
        story.append(_p(c["name"], "H3Custom"))
        story.append(_p(c["explanation"]))

    if k["definitions"]:
        story.append(_p("Key Definitions", "H2Custom"))
        for d in k["definitions"]:
            story.append(_p(f"<b>{d['term']}</b>: {d['definition']}"))

    if k["formulae"]:
        story.append(_p("Formulae", "H2Custom"))
        for f in k["formulae"]:
            story.append(_p(f"<b>{f['name']}</b> — {f['expression']}"))
            story.append(_p(f["explanation"]))

    if k["common_misconceptions"]:
        story.append(_p("Common Misconceptions", "H2Custom"))
        for m in k["common_misconceptions"]:
            story.append(_p(f"<b>Misconception:</b> {m['misconception']}"))
            story.append(_p(f"<b>Correction:</b> {m['correction']}"))

    story.append(PageBreak())
    story.append(_p("Activities by Period", "H2Custom"))
    for period_activities in tkp["activity_plan"]["periods"]:
        story.append(_p(f"Period {period_activities['period_number']}", "H3Custom"))
        for act in period_activities["activities"]:
            story.append(_p(f"<b>{act['name']}</b> ({act['activity_type']}, {act['duration_minutes']} min)"))
            story.append(_p(f"Materials: {', '.join(act['materials_needed'])}"))
            story.append(_p(act["teacher_instructions"]))
            story.append(_p(f"<i>Success criteria: {act['success_criteria']}</i>"))
            story.append(Spacer(1, 0.3 * cm))

    story.append(PageBreak())
    story.append(_p("Learning Gap Analysis", "H2Custom"))
    for period_gaps in tkp["gap_analysis"]["periods"]:
        story.append(_p(f"Period {period_gaps['period_number']}", "H3Custom"))
        for gap in period_gaps["gaps"]:
            story.append(_p(f"<b>[{gap['severity']}] {gap['misconception']}</b>"))
            story.append(_p(f"Diagnostic: {gap['diagnostic_question']}"))
            story.append(_p(f"Remedy: {gap['remedial_action']}"))
            story.append(Spacer(1, 0.3 * cm))

    return _build_doc(output_path, "Teacher Guide", story)


# ---------- Assessment Book PDF ----------

def export_assessment_book_pdf(tkp: dict, output_path: str) -> str:
    story = [
        _p(f"Assessment Book: {tkp['classification']['topic']}", "H1Custom"),
        _p(f"{tkp['classification']['subject']} | {tkp['classification']['grade_level']}", "MetaCustom"),
        Spacer(1, 0.5 * cm),
    ]

    for period_assess in tkp["assessment_plan"]["periods"]:
        story.append(_p(f"Period {period_assess['period_number']}", "H2Custom"))

        if period_assess["mcqs"]:
            story.append(_p("Multiple Choice Questions", "H3Custom"))
            for i, mcq in enumerate(period_assess["mcqs"], 1):
                story.append(_p(f"{i}. {mcq['question']}"))
                for j, opt in enumerate(mcq["options"]):
                    marker = chr(97 + j)  # a, b, c, d
                    story.append(_p(f"({marker}) {opt}", "OptionCustom"))
                story.append(_p(f"<i>Answer: {mcq['correct_answer']} — {mcq['explanation']}</i>", "MetaCustom"))
                story.append(Spacer(1, 0.2 * cm))

        if period_assess["short_answer"]:
            story.append(_p("Short Answer Questions", "H3Custom"))
            for i, q in enumerate(period_assess["short_answer"], 1):
                story.append(_p(f"{i}. {q['question']}"))
                story.append(_p(f"<i>Model answer: {q['model_answer']}</i>", "MetaCustom"))
                story.append(_p(f"<i>Rubric: {q['rubric']}</i>", "MetaCustom"))
                story.append(Spacer(1, 0.2 * cm))

        if period_assess["long_answer"]:
            story.append(_p("Long Answer Questions", "H3Custom"))
            for i, q in enumerate(period_assess["long_answer"], 1):
                story.append(_p(f"{i}. {q['question']}"))
                story.append(_p(f"<i>Model answer: {q['model_answer']}</i>", "MetaCustom"))
                story.append(_p(f"<i>Rubric: {q['rubric']}</i>", "MetaCustom"))
                story.append(Spacer(1, 0.2 * cm))

        if period_assess["numerical_problems"]:
            story.append(_p("Numerical Problems", "H3Custom"))
            for i, q in enumerate(period_assess["numerical_problems"], 1):
                story.append(_p(f"{i}. {q['question']}"))
                story.append(_p(f"<i>Solution: {q['solution_steps']}</i>", "MetaCustom"))
                story.append(_p(f"<i>Answer: {q['final_answer']}</i>", "MetaCustom"))
                story.append(Spacer(1, 0.2 * cm))

        story.append(PageBreak())

    if story and isinstance(story[-1], PageBreak):
        story.pop()

    return _build_doc(output_path, "Assessment Book", story)


# ---------- Convenience: export all three at once ----------

def export_all_pdfs(tkp: dict, output_dir: str) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    paths = {
        "lesson_plans": export_lesson_plans_pdf(tkp, os.path.join(output_dir, "lesson_plans.pdf")),
        "teacher_guide": export_teacher_guide_pdf(tkp, os.path.join(output_dir, "teacher_guide.pdf")),
        "assessment_book": export_assessment_book_pdf(tkp, os.path.join(output_dir, "assessment_book.pdf")),
    }
    return paths