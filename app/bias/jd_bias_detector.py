"""
app/bias/jd_bias_detector.py - Informational Job Description Quality & Bias Detector.

Audits Job Descriptions for overly narrow phrasing, pedigree gatekeeping,
exclusionary language patterns, and inflated experience expectations.

PRINCIPLES:
1. Informational Only: Does NOT modify candidate rankings, weights, or scores.
2. Cautious Language: Uses guidance language ("Consider reviewing...") rather than definitive labels.
3. No Candidate Demographics: Does NOT predict or infer demographic attributes of candidates.
4. Actionable: Provides neutral, constructive rephrasing suggestions for recruiters.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from app.models import JobDescription


@dataclass
class BiasFlag:
    """Represents a single detected instance of potentially narrow or exclusionary phrasing."""
    phrase: str
    category: str
    severity: str  # "High", "Medium", "Low"
    rationale: str
    suggestion: str
    source_snippet: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phrase": self.phrase,
            "category": self.category,
            "severity": self.severity,
            "rationale": self.rationale,
            "suggestion": self.suggestion,
            "source_snippet": self.source_snippet
        }


@dataclass
class JDBiasReport:
    """Comprehensive quality and bias audit report for a Job Description."""
    job_title: str
    total_flags: int
    overall_risk: str  # "Clean / Low Risk", "Moderate Risk", "High Risk"
    flags: List[BiasFlag] = field(default_factory=list)
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_title": self.job_title,
            "total_flags": self.total_flags,
            "overall_risk": self.overall_risk,
            "summary": self.summary,
            "recommendations": self.recommendations,
            "flags": [f.to_dict() for f in self.flags]
        }


class JDBiasDetector:
    """
    Scans Job Descriptions for language patterns that may unnecessarily restrict the talent pool.
    """

    # 1. Educational / Pedigree Gatekeeping Patterns
    PEDIGREE_PATTERNS = [
        (
            r"\b(?:tier[- ]?1\s+(?:colleges?|institutes?|engineering|universit(?:y|ies))|top[- ]?(?:tier|rank(?:ed)?)\s+(?:colleges?|universit(?:y|ies)))\b",
            "Educational Pedigree Gatekeeping",
            "High",
            "Specifying institution tier or prestige excludes skilled candidates from diverse educational backgrounds.",
            "Replace with competency evaluation: 'Degree in Computer Science, related technical field, or equivalent practical experience.'"
        ),
        (
            r"\b(?:ivy\s+league|iit\s+only|nit\s+only|bits\s+only|premier\s+institutes?\s+only)\b",
            "Exclusive Institution Requirement",
            "High",
            "Restricting to specific named institutions severely narrows candidate diversity without measuring individual ability.",
            "Remove specific university restrictions and evaluate demonstrated project portfolio and technical problem-solving."
        ),
        (
            r"\b(?:gpa\s*(?:>|>=|above|of\s*at\s*least)?\s*[89]\.[0-9]|cgpa\s*(?:>|>=|above)?\s*[89]\.[0-9]|90%\s+and\s+above)\b",
            "Excessive Academic Cutoff",
            "Medium",
            "High GPA cutoffs often correlate with socioeconomic factors rather than practical software engineering capability.",
            "Consider lowering or waiving strict GPA thresholds in favor of technical assessments or practical coding repositories."
        )
    ]

    # 2. Corporate Pedigree / Brand Bias Patterns
    CORPORATE_PATTERNS = [
        (
            r"\b(?:ex[- ]?faang|ex[- ]?manga|faang\s+experience|tier[- ]?1\s+product\s+compan(?:y|ies)|top\s+tech\s+compan(?:y|ies)\s+only)\b",
            "Employer Brand Exclusivity",
            "Medium",
            "Demanding past employment at specific brand-name tech companies unfairly disadvantages high performers from startups, open-source, or non-tech sectors.",
            "Focus on functional scale: 'Experience building scalable, distributed systems handling high concurrency.'"
        )
    ]

    # 3. Hyper-Aggressive / Non-Inclusive Culture Phrasing
    CULTURE_PATTERNS = [
        (
            r"\b(?:rockstar|ninja|guru|wizard|coding\s+jedi|superhero)\b",
            "Hyper-Aggressive / Jargon Phrasing",
            "Low",
            "Buzzwords like 'rockstar' or 'ninja' can discourage qualified, collaborative candidates who perceive an ego-driven or unsustainable culture.",
            "Use objective role descriptors: 'Collaborative software engineer passionate about clean architecture and reliable systems.'"
        ),
        (
            r"\b(?:work\s+hard\s+play\s+hard|24/?7\s+availability|round[- ]the[- ]clock\s+commitment|whatever\s+it\s+takes\s+attitude|fast[- ]paced\s+high[- ]stress)\b",
            "Unsustainable Work Expectations",
            "High",
            "Phrases suggesting mandatory round-the-clock availability often discourage candidates with family, caregiving, or work-life balance responsibilities.",
            "Rephrase to focus on outcomes: 'Proactive problem solver with strong time management skills and a commitment to high-quality delivery.'"
        ),
        (
            r"\b(?:native\s+english\s+speaker|native\s+speaker\s+only)\b",
            "Potentially Discriminatory Language Requirement",
            "High",
            "Demanding 'native' speech can exclude fluent non-native professionals and may raise legal or equal opportunity concerns.",
            "Focus strictly on functional proficiency: 'Strong written and verbal professional communication skills in English.'"
        )
    ]

    # 4. Unnecessarily Rigid Phrasing / Technology Lock-In
    RIGID_PATTERNS = [
        (
            r"\b(?:strictly\s+mandatory|non[- ]negotiable\s+requirement|must\s+have\s+exactly\s+\d+\s+years)\b",
            "Unusually Inflexible Requirement Phrasing",
            "Low",
            "Rigid, absolute phrasing often deters qualified candidates who possess strong adjacent skills and fast learning capability.",
            "Consider softening to: 'Demonstrated experience with X, or significant proficiency in equivalent modern frameworks.'"
        )
    ]

    @classmethod
    def analyze(cls, jd: JobDescription) -> JDBiasReport:
        """Analyzes a JobDescription object and returns a JDBiasReport."""
        return cls.analyze_text(
            raw_text=jd.raw_text,
            job_title=jd.title,
            exp_required=jd.experience_years_required
        )

    @classmethod
    def analyze_text(
        cls,
        raw_text: str,
        job_title: str = "Job Opening",
        exp_required: float = 0.0
    ) -> JDBiasReport:
        """
        Scans raw text against quality and narrow-phrasing patterns.
        Purely informational: does not alter matching or ranking.
        """
        flags: List[BiasFlag] = []

        if not raw_text or not raw_text.strip():
            return JDBiasReport(
                job_title=job_title,
                total_flags=0,
                overall_risk="Clean / Low Risk",
                summary="No text provided for analysis.",
                recommendations=[]
            )

        text_lower = raw_text.lower()

        # Helper to extract surrounding context for a match
        def get_snippet(span_start: int, span_end: int) -> str:
            start = max(0, span_start - 40)
            end = min(len(raw_text), span_end + 40)
            snippet = raw_text[start:end].replace("\n", " ").strip()
            return f"...{snippet}..."

        # 1. Scan Pedigree
        for pattern, cat, sev, rat, sug in cls.PEDIGREE_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                flags.append(BiasFlag(
                    phrase=match.group(0),
                    category=cat,
                    severity=sev,
                    rationale=rat,
                    suggestion=sug,
                    source_snippet=get_snippet(match.start(), match.end())
                ))

        # 2. Scan Corporate Brand Exclusivity
        for pattern, cat, sev, rat, sug in cls.CORPORATE_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                flags.append(BiasFlag(
                    phrase=match.group(0),
                    category=cat,
                    severity=sev,
                    rationale=rat,
                    suggestion=sug,
                    source_snippet=get_snippet(match.start(), match.end())
                ))

        # 3. Scan Culture & Aggressive Phrasing
        for pattern, cat, sev, rat, sug in cls.CULTURE_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                flags.append(BiasFlag(
                    phrase=match.group(0),
                    category=cat,
                    severity=sev,
                    rationale=rat,
                    suggestion=sug,
                    source_snippet=get_snippet(match.start(), match.end())
                ))

        # 4. Scan Rigid Phrasing
        for pattern, cat, sev, rat, sug in cls.RIGID_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                flags.append(BiasFlag(
                    phrase=match.group(0),
                    category=cat,
                    severity=sev,
                    rationale=rat,
                    suggestion=sug,
                    source_snippet=get_snippet(match.start(), match.end())
                ))

        # 5. Check for Inflated Experience on Junior / Intern Roles
        is_junior_role = any(term in job_title.lower() for term in ["intern", "junior", "trainee", "fresher", "entry level", "entry-level"])
        if is_junior_role and exp_required >= 2.5:
            flags.append(BiasFlag(
                phrase=f"Required experience: {exp_required:.1f} years",
                category="Inflated Experience Requirement",
                severity="High" if exp_required >= 4.0 else "Medium",
                rationale=(
                    f"Job title indicates an entry/junior role ('{job_title}'), but asks for {exp_required:.1f} years of experience. "
                    "This discourages promising graduates and students with strong project portfolios."
                ),
                suggestion="For junior and internship positions, calibrate required experience to 0–1 years and evaluate demonstrated project quality.",
                source_snippet=f"Role: {job_title} | Experience Required: {exp_required:.1f} years"
            ))

        # Determine overall risk
        high_count = sum(1 for f in flags if f.severity == "High")
        med_count = sum(1 for f in flags if f.severity == "Medium")

        if high_count > 0:
            overall_risk = "High Risk"
        elif med_count > 0:
            overall_risk = "Moderate Risk"
        elif flags:
            overall_risk = "Low Risk"
        else:
            overall_risk = "Clean / Low Risk"

        # Formulate summary and recommendations
        if not flags:
            summary = "No exclusionary phrasing or unnecessary pedigree gatekeeping detected. The JD uses standard professional language."
            recs = ["JD language appears fair, inclusive, and appropriately focused on functional competencies."]
        else:
            summary = (
                f"Identified {len(flags)} potential item(s) to review ({high_count} High, {med_count} Medium). "
                "Consider revising flagged items to broaden the qualified candidate pool."
            )
            recs = list(dict.fromkeys([f.suggestion for f in flags]))

        return JDBiasReport(
            job_title=job_title,
            total_flags=len(flags),
            overall_risk=overall_risk,
            flags=flags,
            summary=summary,
            recommendations=recs
        )
