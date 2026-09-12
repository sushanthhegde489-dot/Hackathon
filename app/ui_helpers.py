"""
ui_helpers.py - Reusable helper functions, presets, and validation routines
for the Streamlit Recruiter Application.
"""

import csv
import io
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

from app.config import RankingConfig, DEFAULT_RANKING_CONFIG
from app.models import CandidateResult, JobDescription, Resume

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# 1. PRESETS & SENSITIVITY CONFIGURATION
# -----------------------------------------------------------------------------

PRESET_CONFIGS: Dict[str, Dict[str, Any]] = {
    "Recommended": {
        "keyword_weight": 0.40,
        "semantic_weight": 0.60,
        "required_skill_weight": 0.70,
        "preferred_skill_weight": 0.30,
        "semantic_noise_threshold": 0.18,
        "experience_penalty_per_year": 0.05,
        "maximum_experience_penalty": 0.20,
        "weights_label": "40% Keyword / 60% Semantic",
        "description": "Balanced matching that gives semantic evidence slightly more influence than exact skill overlap."
    },
    "Skills-first": {
        "keyword_weight": 0.25,
        "semantic_weight": 0.75,
        "required_skill_weight": 0.70,
        "preferred_skill_weight": 0.30,
        "semantic_noise_threshold": 0.18,
        "experience_penalty_per_year": 0.05,
        "maximum_experience_penalty": 0.20,
        "weights_label": "25% Keyword / 75% Semantic",
        "description": "Prioritizes project depth and semantic alignment over exact keyword matches."
    },
    "Strict compliance": {
        "keyword_weight": 0.60,
        "semantic_weight": 0.40,
        "required_skill_weight": 0.70,
        "preferred_skill_weight": 0.30,
        "semantic_noise_threshold": 0.18,
        "experience_penalty_per_year": 0.05,
        "maximum_experience_penalty": 0.20,
        "weights_label": "60% Keyword / 40% Semantic",
        "description": "Prioritizes exact mandatory skills for strict qualification requirements."
    },
    "Custom configuration": {
        "keyword_weight": 0.40,
        "semantic_weight": 0.60,
        "required_skill_weight": 0.70,
        "preferred_skill_weight": 0.30,
        "semantic_noise_threshold": 0.18,
        "experience_penalty_per_year": 0.05,
        "maximum_experience_penalty": 0.20,
        "weights_label": "Manual Weight Allocation",
        "description": "Manually adjust scoring weights and calibration parameters below."
    }
}

KEYWORD_STUFFING_THRESHOLD = 0.60

def check_keyword_stuffing_warning(keyword_weight: float) -> Tuple[bool, str]:
    """
    Returns a warning if keyword weight is >= 0.60.
    At this threshold, adversarial keyword stuffing can leapfrog qualified candidates.
    """
    if keyword_weight >= KEYWORD_STUFFING_THRESHOLD:
        warning_msg = (
            f"Adversarial Risk Warning: Keyword weight is {keyword_weight:.2f} (>= 0.60). "
            "High keyword weights allow keyword-stuffed resumes to outrank qualified candidates."
        )
        return True, warning_msg
    return False, ""

# -----------------------------------------------------------------------------
# 2. SAMPLE JOB DESCRIPTIONS
# -----------------------------------------------------------------------------

SAMPLE_JOB_DESCRIPTIONS: Dict[str, Dict[str, Any]] = {
    "Backend Engineer (Python / Cloud / Microservices)": {
        "title": "Backend Software Engineer",
        "filename": "sample_backend_engineer_jd.txt",
        "text": """Job Title: Backend Software Engineer
Location: Remote / Hybrid
Experience Required: 2+ years of professional backend engineering experience

About the Role:
We are looking for a skilled Backend Software Engineer to build scalable microservices and APIs.
You will architect distributed backend systems, design resilient database schemas, and collaborate with DevOps.

Required Qualifications:
- Strong proficiency in Python and modern backend frameworks (FastAPI, Django, or Flask)
- Solid experience with relational databases, specifically PostgreSQL or MySQL
- Experience designing and building RESTful APIs and Microservices architectures
- Hands-on experience with CI/CD pipelines and version control (Git)
- Must have at least 2 years of relevant software development experience

Preferred Qualifications:
- Hands-on experience with containerization using Docker and orchestration with Kubernetes
- Familiarity with cloud infrastructure, particularly AWS or GCP
- Experience with in-memory caching solutions like Redis
- Good understanding of asynchronous task queues and messaging systems (Celery, RabbitMQ)

Responsibilities:
- Build, test, and deploy resilient API endpoints.
- Optimize complex database queries and ensure high data availability.
- Write clean, well-tested code following best engineering practices.
"""
    },
    "Full Stack Developer (React / Node.js / TypeScript)": {
        "title": "Full Stack Developer",
        "filename": "sample_fullstack_developer_jd.txt",
        "text": """Job Title: Full Stack Developer
Experience Required: 1+ years of full stack web development experience

Overview:
We are hiring an energetic Full Stack Developer to build modern web applications.
You will develop responsive frontend interfaces and integrate them with high-performance backend services.

Required Skills:
- Proficiency in React and modern JavaScript/TypeScript
- Server-side development with Node.js and Express
- Experience building and consuming REST APIs
- Knowledge of modern CSS, HTML, and responsive UI frameworks (Tailwind CSS)
- Experience with SQL or MongoDB databases

Preferred Qualifications:
- Familiarity with Next.js or GraphQL
- Exposure to cloud deployment on AWS or Azure
- Experience writing automated unit and integration tests

What You'll Do:
- Design and implement end-to-end features from UI to database.
- Collaborate with design and product teams to deliver intuitive user experiences.
"""
    }
}

# -----------------------------------------------------------------------------
# 3. DEMO RESUME SELECTION (15–18 PDF BATCH FROM data/resumes/)
# -----------------------------------------------------------------------------

def get_demo_resume_paths(base_dir: Optional[Path] = None, target_count: int = 18) -> List[Path]:
    """
    Selects a curated, diverse batch of 15–18 real PDF resumes from data/resumes/.
    Includes candidates from multiple engineering domains:
    - Python developers (strong alignment)
    - SDE / Full-stack developers (moderate-high alignment)
    - Data scientists / AI developers (partial alignment)
    - App developers / Web developers (domain variance)
    - Cyber security / IT support (lateral tech)
    - Content / Sales / Social Media (unrelated controls)
    """
    if base_dir is None:
        # Default project root: Hackathon/data/resumes
        candidate_dir = Path(__file__).resolve().parent.parent / "data" / "resumes"
    else:
        candidate_dir = Path(base_dir)

    if not candidate_dir.exists() or not candidate_dir.is_dir():
        logger.warning(f"Resume directory {candidate_dir} not found.")
        return []

    # Curated filenames covering relevant, adjacent, and baseline candidate profiles
    preferred_curated_names = [
        "python_dev__karan_verma.pdf",
        "python_dev__sneha_reddy.pdf",
        "sde__arjun_desai.pdf",
        "sde__ishaan_kapoor.pdf",
        "Python_Developer_Resume_1_Karan_Malhotra.pdf",
        "Python_Developer_Resume_2_Ananya_Reddy.pdf",
        "SDE_Resume_1_Aditya_Joshi.pdf",
        "SDE_Resume_2_Meera_Pillai.pdf",
        "ai_dev__rohan_mehta.pdf",
        "data_scientist__nikhil_rao.pdf",
        "web_dev__aditya_kulkarni.pdf",
        "app_dev__rahul_bose.pdf",
        "cyber_security__vikram_singh.pdf",
        "it_support__deepak_yadav.pdf",
        "founder_s_office__siddharth_rao.pdf",
        "marketing__harsh_vardhan.pdf",
        "sales__aman_tiwari.pdf",
        "social_media_intern__sara_khan.pdf"
    ]

    selected: List[Path] = []
    for name in preferred_curated_names:
        p = candidate_dir / name
        if p.exists() and p.is_file():
            selected.append(p)

    # If some curated files are missing, supplement with discovered PDFs
    if len(selected) < target_count:
        all_pdfs = sorted(list(candidate_dir.glob("*.pdf")), key=lambda p: p.name.lower())
        for p in all_pdfs:
            if p not in selected:
                selected.append(p)
            if len(selected) >= target_count:
                break

    return selected[:target_count]

# -----------------------------------------------------------------------------
# 4. BATCH VALIDATION & HEALTH CHECK
# -----------------------------------------------------------------------------

def validate_resume_batch(items: List[Tuple[str, str]]) -> Dict[str, Any]:
    """
    Validates a batch of (filename, raw_text) resumes before ranking.
    Checks:
    - Candidate count (optimal: 15–18)
    - Duplicate filenames
    - Empty or unparseable resumes
    """
    total = len(items)
    filenames = [fn for fn, _ in items]
    unique_filenames = set()
    duplicates = []
    for fn in filenames:
        if fn in unique_filenames:
            duplicates.append(fn)
        else:
            unique_filenames.add(fn)

    empty_files = [fn for fn, text in items if not text or not text.strip()]
    valid_items = [(fn, text) for fn, text in items if text and text.strip()]

    # Count validation status
    if 15 <= total <= 18:
        count_status = "optimal"
        count_message = f"Optimal batch size: {total} candidates loaded (meets hackathon standard 15–18)."
    elif total < 15:
        count_status = "below_optimal"
        count_message = f"Batch size: {total} candidate(s). The hackathon benchmark recommends 15–18 resumes for full calibration."
    else:
        count_status = "above_optimal"
        count_message = f"Batch size: {total} candidates. All will be processed and ranked."

    return {
        "total_count": total,
        "valid_count": len(valid_items),
        "count_status": count_status,
        "count_message": count_message,
        "duplicates": duplicates,
        "empty_files": empty_files,
        "has_duplicates": len(duplicates) > 0,
        "has_empty": len(empty_files) > 0,
        "valid_items": valid_items
    }

# -----------------------------------------------------------------------------
# 5. LEADERBOARD EXPORT FORMATTERS (CSV & JSON)
# -----------------------------------------------------------------------------

def format_percentage(val: float) -> str:
    """Formats a 0.0–1.0 score as a readable percentage string e.g. 82.5%."""
    return f"{round(val * 100, 1):.1f}%"

def generate_leaderboard_csv(results: List[CandidateResult]) -> str:
    """Generates an auditable CSV representation of the full candidate leaderboard."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Rank",
        "Candidate Name",
        "Filename",
        "Final Score (%)",
        "Base Score (%)",
        "Keyword Score (%)",
        "Keyword Contribution (%)",
        "Semantic Score (%)",
        "Semantic Contribution (%)",
        "Experience (Yrs)",
        "Penalty (%)",
        "Matched Required Skills",
        "Missing Required Skills",
        "Matched Preferred Skills",
        "Ranking Rationale",
        "Score Formula Used"
    ])

    for i, res in enumerate(results, 1):
        kw = res.keyword_breakdown
        writer.writerow([
            i,
            res.resume.candidate_name,
            res.resume.filename,
            format_percentage(res.final_score),
            format_percentage(res.diagnostics.base_score),
            format_percentage(res.keyword_score),
            format_percentage(res.diagnostics.keyword_contribution),
            format_percentage(res.semantic_score),
            format_percentage(res.diagnostics.semantic_contribution),
            f"{res.resume.experience_years:.1f}",
            format_percentage(res.penalties.total_penalty),
            ", ".join(kw.matched_required_skills),
            ", ".join(kw.missing_required_skills),
            ", ".join(kw.matched_preferred_skills),
            res.ranking_reason,
            f"Final = max(0, min(1, (Keyword * {res.diagnostics.keyword_weight} + Semantic * {res.diagnostics.semantic_weight}) - Penalty))"
        ])

    return output.getvalue()

def generate_leaderboard_json(results: List[CandidateResult]) -> str:
    """Generates structured JSON representation of the complete leaderboard."""
    data = []
    for i, res in enumerate(results, 1):
        item = res.to_dict()
        item["rank"] = i
        item["final_score_pct"] = format_percentage(res.final_score)
        data.append(item)
    return json.dumps(data, indent=2)
