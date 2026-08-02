# app/models.py
"""
Pydantic schemas for every pipeline stage's output. Grows as we add stages.
Every stage validates the LLM's raw JSON against its schema here before
passing data downstream — catches hallucinated fields/types immediately
instead of a confusing KeyError three stages later.
"""
from pydantic import BaseModel
from typing import Optional, List


class DocumentClassification(BaseModel):
    subject: str
    grade_level: str
    difficulty: str          # "Beginner" / "Intermediate" / "Advanced"
    topic: str
    chapter: Optional[str] = None
    category: str            # "STEM" / "Humanities" / "Language" / "Arts" / etc.
    language: str
    confidence: float 
# app/models.py — ADD these classes below DocumentClassification
# (keep DocumentClassification as-is, just append the following)

class Concept(BaseModel):
    name: str
    explanation: str

class Definition(BaseModel):
    term: str
    definition: str

class Formula(BaseModel):
    name: str
    expression: str
    explanation: str

class Example(BaseModel):
    description: str
    relates_to_concept: Optional[str] = None

class Misconception(BaseModel):
    misconception: str
    correction: str

class KnowledgeExtraction(BaseModel):
    learning_objectives: List[str]
    prerequisites: List[str]
    concepts: List[Concept]
    definitions: List[Definition]
    formulae: List[Formula]              # empty list for non-STEM content, not omitted
    keywords: List[str]
    examples: List[Example]
    applications: List[str]
    common_misconceptions: List[Misconception]    
class Period(BaseModel):
    period_number: int
    title: str
    duration_minutes: int
    learning_objectives: List[str]      # subset relevant to this period
    concepts_covered: List[str]         # names, referencing Stage 3 concepts
    sequencing_rationale: str           # why this content goes here / this order

class TeachingPlan(BaseModel):
    total_periods: int
    periods: List[Period]
    overall_sequencing_notes: str           # 0-1
class PeriodContent(BaseModel):
    period_number: int
    entry_ticket: str
    teacher_script: str
    blackboard_notes: str
    classroom_activities: List[str]     # brief activity names/descriptions; Stage 6 elaborates these
    checkpoint_questions: List[str]
    exit_ticket: str
    homework: str
    mentor_moment: str                  # motivational anecdote

class ClassroomContent(BaseModel):
    periods: List[PeriodContent]  
class ActivitySpec(BaseModel):
    name: str
    activity_type: str          # "Demonstration" / "Role Play" / "Experiment" / "Discussion" / "Group Work" / etc.
    duration_minutes: int
    materials_needed: List[str]
    teacher_instructions: str
    success_criteria: str

class PeriodActivities(BaseModel):
    period_number: int
    activities: List[ActivitySpec]

class ActivityPlan(BaseModel):
    periods: List[PeriodActivities]     
class MCQ(BaseModel):
    question: str
    options: List[str]           # exactly 4 options
    correct_answer: str          # must match one of options exactly
    explanation: str

class ShortAnswerQuestion(BaseModel):
    question: str
    model_answer: str
    rubric: str                  # brief scoring guidance

class LongAnswerQuestion(BaseModel):
    question: str
    model_answer: str
    rubric: str

class NumericalProblem(BaseModel):
    question: str
    solution_steps: str
    final_answer: str

class PeriodAssessment(BaseModel):
    period_number: int
    mcqs: List[MCQ]
    short_answer: List[ShortAnswerQuestion]
    long_answer: List[LongAnswerQuestion]
    numerical_problems: List[NumericalProblem]   # empty list if not applicable

class AssessmentPlan(BaseModel):
    periods: List[PeriodAssessment]   
class LearningGap(BaseModel):
    misconception: str
    diagnostic_question: str      # a question a teacher can ask to detect this gap
    severity: str                 # "Low" / "Medium" / "High"
    remedial_action: str          # what the teacher should do if detected

class PeriodGapAnalysis(BaseModel):
    period_number: int
    gaps: List[LearningGap]

class GapAnalysisReport(BaseModel):
    periods: List[PeriodGapAnalysis]   
# app/models.py — ADD below GapAnalysisReport

class ValidationIssue(BaseModel):
    severity: str            # "Info" / "Warning" / "Critical"
    category: str            # "schema" / "missing_content" / "hallucination" / "consistency"
    description: str
    location: Optional[str] = None   # e.g. "Period 3" or "Stage 5"

class ValidationReport(BaseModel):
    passed: bool              # True if no Critical issues
    issues: List[ValidationIssue]
    objectives_coverage_pct: float    # % of Stage 4 objectives actually covered downstream
class TKPMetadata(BaseModel):
    source_filename: str
    generated_at: str          # ISO timestamp
    target_periods: int
    period_duration_minutes: int

class TeacherKnowledgePackage(BaseModel):
    metadata: TKPMetadata
    classification: DocumentClassification
    knowledge: KnowledgeExtraction
    teaching_plan: TeachingPlan
    classroom_content: ClassroomContent
    activity_plan: ActivityPlan
    assessment_plan: AssessmentPlan
    gap_analysis: GapAnalysisReport
    validation_report: ValidationReport           