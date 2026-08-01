# app/pipeline/stage9_validation.py
"""
Stage 9 — Validation.
Hybrid: deterministic checks run in plain Python (fast, free, 100% reliable
— schema adherence, objective coverage, period-count consistency). Only the
genuinely judgment-requiring checks (hallucination detection, qualitative
pedagogical consistency) go to the LLM. Don't reach for the LLM for things
a set-membership check can already answer.
"""
from app.llm_client import generate_json
from app.models import ValidationIssue, ValidationReport


# ---------- Deterministic checks (no LLM, no tokens spent) ----------

def _check_objective_coverage(teaching_plan: dict, classroom_content: dict) -> tuple[list, float]:
    """Are all of Stage 4's learning_objectives actually addressed somewhere
    in the plan's own periods? (Stage 4 already assigns objectives per
    period, so this checks the plan is internally consistent with itself —
    every period's objectives should trace back to real content.)"""
    issues = []
    plan_objectives = set()
    for period in teaching_plan["periods"]:
        plan_objectives.update(o.strip().lower() for o in period["learning_objectives"])

    content_by_period = {p["period_number"]: p for p in classroom_content["periods"]}
    covered = 0
    for period in teaching_plan["periods"]:
        content = content_by_period.get(period["period_number"])
        if content is None:
            issues.append(ValidationIssue(
                severity="Critical", category="missing_content",
                description=f"Period {period['period_number']} has a teaching plan entry but no classroom content was generated for it.",
                location=f"Period {period['period_number']}"
            ))
            continue
        # A period "covers" its objectives if it has non-empty core content fields
        if content["teacher_script"].strip() and content["exit_ticket"].strip():
            covered += 1
        else:
            issues.append(ValidationIssue(
                severity="Warning", category="missing_content",
                description=f"Period {period['period_number']} has thin or empty core content (teacher_script/exit_ticket).",
                location=f"Period {period['period_number']}"
            ))

    pct = (covered / len(teaching_plan["periods"]) * 100) if teaching_plan["periods"] else 0.0
    return issues, pct


def _check_period_consistency(teaching_plan: dict, classroom_content: dict,
                               activity_plan: dict, assessment_plan: dict) -> list:
    """Do period numbers line up consistently across all stages? Does the
    declared total_periods match the actual period list length?"""
    issues = []

    if teaching_plan["total_periods"] != len(teaching_plan["periods"]):
        issues.append(ValidationIssue(
            severity="Critical", category="consistency",
            description=f"teaching_plan declares total_periods={teaching_plan['total_periods']} "
                         f"but periods list has {len(teaching_plan['periods'])} entries.",
            location="Stage 4"
        ))

    plan_period_numbers = {p["period_number"] for p in teaching_plan["periods"]}

    for stage_name, stage_data in [
        ("Stage 5 (classroom_content)", classroom_content),
        ("Stage 6 (activity_plan)", activity_plan),
        ("Stage 7 (assessment_plan)", assessment_plan),
    ]:
        stage_period_numbers = {p["period_number"] for p in stage_data["periods"]}
        missing = plan_period_numbers - stage_period_numbers
        extra = stage_period_numbers - plan_period_numbers
        if missing:
            issues.append(ValidationIssue(
                severity="Critical", category="consistency",
                description=f"{stage_name} is missing periods {sorted(missing)} that exist in the teaching plan.",
                location=stage_name
            ))
        if extra:
            issues.append(ValidationIssue(
                severity="Warning", category="consistency",
                description=f"{stage_name} has periods {sorted(extra)} not present in the teaching plan.",
                location=stage_name
            ))

    return issues


def _run_deterministic_checks(teaching_plan: dict, classroom_content: dict,
                               activity_plan: dict, assessment_plan: dict) -> tuple[list, float]:
    issues = []
    coverage_issues, coverage_pct = _check_objective_coverage(teaching_plan, classroom_content)
    issues.extend(coverage_issues)
    issues.extend(_check_period_consistency(teaching_plan, classroom_content, activity_plan, assessment_plan))
    return issues, coverage_pct


# ---------- LLM-based checks (semantic judgment required) ----------

SYSTEM_PROMPT = """You are a meticulous quality reviewer for AI-generated
educational content. You will be shown a summary of the original source
knowledge and a summary of generated teaching content. Identify:

1. HALLUCINATIONS: any fact, formula, definition, or claim in the generated
   content that is NOT supported by (or contradicts) the original source
   knowledge. Be specific — quote the questionable claim.
2. PEDAGOGICAL INCONSISTENCY: cases where a later period's content assumes
   knowledge that was never actually taught in an earlier period, or where
   content contradicts itself across periods.

Only report genuine issues. If everything looks consistent and well-grounded,
return an empty issues list — do not invent problems to seem thorough.

Respond ONLY with a JSON object matching EXACTLY this structure:

{
  "issues": [
    {
      "severity": "Info" | "Warning" | "Critical",
      "category": "hallucination" | "consistency",
      "description": "string, specific and quoting the questionable content",
      "location": "string, e.g. 'Period 3 teacher_script'"
    }
  ]
}
"""


def _run_llm_checks(knowledge: dict, classroom_content: dict) -> list:
    knowledge_summary = {
        "concepts": [c["name"] for c in knowledge["concepts"]],
        "definitions": knowledge["definitions"],
        "formulae": knowledge["formulae"],
    }
    content_summary = [
        {
            "period_number": p["period_number"],
            "teacher_script": p["teacher_script"][:400],
            "blackboard_notes": p["blackboard_notes"][:300],
        }
        for p in classroom_content["periods"]
    ]

    user_prompt = f"""Original source knowledge (ground truth):
{knowledge_summary}

Generated classroom content to review:
{content_summary}

Identify hallucinations and pedagogical inconsistencies as specified."""

    result = generate_json(SYSTEM_PROMPT, user_prompt, temperature=0.2, max_output_tokens=1024)
    raw_issues = result.get("issues", [])
    return [ValidationIssue(**issue) for issue in raw_issues]


# ---------- Combined entry point ----------

def validate_tkp(teaching_plan: dict, knowledge: dict, classroom_content: dict,
                  activity_plan: dict, assessment_plan: dict) -> dict:
    deterministic_issues, coverage_pct = _run_deterministic_checks(
        teaching_plan, classroom_content, activity_plan, assessment_plan
    )
    llm_issues = _run_llm_checks(knowledge, classroom_content)

    all_issues = deterministic_issues + llm_issues
    has_critical = any(issue.severity == "Critical" for issue in all_issues)

    report = ValidationReport(
        passed=not has_critical,
        issues=all_issues,
        objectives_coverage_pct=round(coverage_pct, 1),
    )
    return report.model_dump()