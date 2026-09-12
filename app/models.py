from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class SkillEvidence:
    """Stores the provenance and contextual evidence for an extracted skill."""
    skill: str
    classification: str  # "required", "preferred", "contextual"
    confidence: float    # 0.0 to 1.0 confidence score
    source_context: str  # Sentence or snippet where the skill appeared
    cue_phrase: str = "" # Cue phrase that triggered classification (e.g. "must have", "nice to have")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill": self.skill,
            "classification": self.classification,
            "confidence": round(self.confidence, 2),
            "source_context": self.source_context,
            "cue_phrase": self.cue_phrase
        }

@dataclass
class JobDescription:
    """
    Represents a Job Description with multi-tier skill classification:
    - required_skills: mandatory/must-have requirements
    - preferred_skills: desirable/nice-to-have qualifications
    - contextual_skills: technologies mentioned in general context without explicit requirement cues
    """
    filename: str
    raw_text: str
    cleaned_text: str = ""
    title: str = "Unknown Job Title"
    required_skills: List[str] = field(default_factory=list)
    preferred_skills: List[str] = field(default_factory=list)
    contextual_skills: List[str] = field(default_factory=list)
    responsibilities: List[str] = field(default_factory=list)
    skill_evidences: Dict[str, SkillEvidence] = field(default_factory=dict)
    experience_years_required: float = 0.0
    sections: Dict[str, str] = field(default_factory=dict)
    other_metadata: Dict[str, Any] = field(default_factory=dict)

    def all_skills(self) -> List[str]:
        """Returns unique union of all detected skills across all tiers."""
        combined = list(dict.fromkeys(self.required_skills + self.preferred_skills + self.contextual_skills))
        return combined

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "title": self.title,
            "required_skills": self.required_skills,
            "preferred_skills": self.preferred_skills,
            "contextual_skills": self.contextual_skills,
            "responsibilities": self.responsibilities,
            "skill_evidences": {k: v.to_dict() for k, v in self.skill_evidences.items()},
            "experience_years_required": self.experience_years_required,
            "sections": list(self.sections.keys()),
            "other_metadata": self.other_metadata
        }

@dataclass
class ExperienceEntry:
    """Represents a single job or internship experience entry in a resume."""
    title: str = ""
    company: str = ""
    duration: str = ""
    years: float = 0.0
    description: str = ""
    technologies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "company": self.company,
            "duration": self.duration,
            "years": self.years,
            "description": self.description,
            "technologies": self.technologies
        }

@dataclass
class ProjectEntry:
    """Represents a project entry in a resume."""
    name: str = ""
    description: str = ""
    technologies: List[str] = field(default_factory=list)
    link: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "technologies": self.technologies,
            "link": self.link
        }

@dataclass
class EducationEntry:
    """Represents an education entry in a resume."""
    degree: str = ""
    institution: str = ""
    year: str = ""
    gpa: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "degree": self.degree,
            "institution": self.institution,
            "year": self.year,
            "gpa": self.gpa
        }

@dataclass
class Resume:
    """
    Represents a Candidate's Resume with structured sections and provenance.
    If detailed entries cannot be reliably extracted, raw section text is preserved
    and structured fields remain empty rather than hallucinating.
    """
    filename: str
    raw_text: str
    cleaned_text: str = ""
    candidate_name: str = "Unknown Candidate"
    email: str = ""
    phone: str = ""
    skills: List[str] = field(default_factory=list)
    experience_years: float = 0.0
    experience_entries: List[ExperienceEntry] = field(default_factory=list)
    projects: List[ProjectEntry] = field(default_factory=list)
    education: List[EducationEntry] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    sections: Dict[str, str] = field(default_factory=dict)
    other_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "candidate_name": self.candidate_name,
            "email": self.email,
            "phone": self.phone,
            "skills": self.skills,
            "experience_years": self.experience_years,
            "experience_entries": [e.to_dict() for e in self.experience_entries],
            "projects": [p.to_dict() for p in self.projects],
            "education": [ed.to_dict() for ed in self.education],
            "certifications": self.certifications,
            "sections": list(self.sections.keys()),
            "other_metadata": self.other_metadata
        }

@dataclass
class KeywordScoreBreakdown:
    """Granular breakdown of keyword matching score and skill evidences."""
    score: float = 0.0
    required_skill_score: float = 0.0
    preferred_skill_score: float = 0.0
    matched_required_skills: List[str] = field(default_factory=list)
    missing_required_skills: List[str] = field(default_factory=list)
    matched_preferred_skills: List[str] = field(default_factory=list)
    missing_preferred_skills: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 4),
            "required_skill_score": round(self.required_skill_score, 4),
            "preferred_skill_score": round(self.preferred_skill_score, 4),
            "matched_required_skills": self.matched_required_skills,
            "missing_required_skills": self.missing_required_skills,
            "matched_preferred_skills": self.matched_preferred_skills,
            "missing_preferred_skills": self.missing_preferred_skills,
            "evidence": self.evidence
        }

@dataclass
class SemanticScoreBreakdown:
    """Granular breakdown of semantic similarity scoring."""
    score: float = 0.0
    strongest_matches: List[Dict[str, Any]] = field(default_factory=list)
    similarity_evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 4),
            "strongest_matches": self.strongest_matches,
            "similarity_evidence": self.similarity_evidence
        }

@dataclass
class PenaltyBreakdown:
    """Breakdown of penalties applied to candidate score (e.g. experience gap)."""
    experience_penalty: float = 0.0
    missing_critical_penalty: float = 0.0
    details: Dict[str, float] = field(default_factory=dict)
    total_penalty: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experience_penalty": round(self.experience_penalty, 4),
            "missing_critical_penalty": round(self.missing_critical_penalty, 4),
            "details": {k: round(v, 4) for k, v in self.details.items()},
            "total_penalty": round(self.total_penalty, 4)
        }

@dataclass
class ScoreDiagnostics:
    """Detailed machine-readable contribution diagnostics for hybrid ranking."""
    keyword_score: float = 0.0
    keyword_weight: float = 0.0
    keyword_contribution: float = 0.0
    semantic_score: float = 0.0
    semantic_weight: float = 0.0
    semantic_contribution: float = 0.0
    base_score: float = 0.0
    experience_penalty: float = 0.0
    total_penalty: float = 0.0
    final_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "keyword_score": round(self.keyword_score, 4),
            "keyword_weight": round(self.keyword_weight, 4),
            "keyword_contribution": round(self.keyword_contribution, 4),
            "semantic_score": round(self.semantic_score, 4),
            "semantic_weight": round(self.semantic_weight, 4),
            "semantic_contribution": round(self.semantic_contribution, 4),
            "base_score": round(self.base_score, 4),
            "experience_penalty": round(self.experience_penalty, 4),
            "total_penalty": round(self.total_penalty, 4),
            "final_score": round(self.final_score, 4)
        }

@dataclass
class CandidateResult:
    """
    Represents the complete matching, scoring, and ranking results for a candidate.
    Structured to cleanly support:
    CandidateResult
    ├── keyword_score
    │   ├── required_skill_score
    │   ├── preferred_skill_score
    │   ├── matched_required_skills
    │   ├── missing_required_skills
    │   └── evidence
    ├── semantic_score
    │   ├── strongest_matches
    │   └── similarity_evidence
    ├── penalties
    ├── final_score
    └── ranking_reason
    """
    resume: Resume
    keyword_breakdown: KeywordScoreBreakdown = field(default_factory=KeywordScoreBreakdown)
    semantic_breakdown: SemanticScoreBreakdown = field(default_factory=SemanticScoreBreakdown)
    penalties: PenaltyBreakdown = field(default_factory=PenaltyBreakdown)
    diagnostics: ScoreDiagnostics = field(default_factory=ScoreDiagnostics)
    final_score: float = 0.0
    rank: int = 0
    ranking_reason: str = ""

    # Backwards compatibility properties
    @property
    def keyword_score(self) -> float:
        return self.keyword_breakdown.score

    @keyword_score.setter
    def keyword_score(self, value: float):
        self.keyword_breakdown.score = value

    @property
    def semantic_score(self) -> float:
        return self.semantic_breakdown.score

    @semantic_score.setter
    def semantic_score(self, value: float):
        self.semantic_breakdown.score = value

    @property
    def matched_skills(self) -> List[str]:
        return list(dict.fromkeys(self.keyword_breakdown.matched_required_skills + self.keyword_breakdown.matched_preferred_skills))

    @matched_skills.setter
    def matched_skills(self, skills: List[str]):
        self.keyword_breakdown.matched_required_skills = skills

    @property
    def missing_skills(self) -> List[str]:
        return self.keyword_breakdown.missing_required_skills

    @missing_skills.setter
    def missing_skills(self, skills: List[str]):
        self.keyword_breakdown.missing_required_skills = skills

    @property
    def justification(self) -> str:
        return self.ranking_reason

    @justification.setter
    def justification(self, value: str):
        self.ranking_reason = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "candidate_name": self.resume.candidate_name,
            "filename": self.resume.filename,
            "base_score": round(self.diagnostics.base_score, 4),
            "final_score": round(self.final_score, 4),
            "diagnostics": self.diagnostics.to_dict(),
            "keyword_score": self.keyword_breakdown.to_dict(),
            "semantic_score": self.semantic_breakdown.to_dict(),
            "penalties": self.penalties.to_dict(),
            "ranking_reason": self.ranking_reason,
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
            "experience_years": self.resume.experience_years
        }
