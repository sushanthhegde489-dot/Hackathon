from typing import Optional, Dict, Any
from app.config import RankingConfig, DEFAULT_RANKING_CONFIG
from app.models import JobDescription, Resume, PenaltyBreakdown


class PenaltyCalculator:
    """
    Calculates transparent, bounded score deductions for candidates.
    
    Principles:
    1. Single Responsibility: Evaluates only explicit negative evidence (e.g., experience gap).
       Does NOT mix in keyword matching or semantic similarity.
    2. Transparent Formula: Penalty is directly proportional to the experience gap,
       scaled by a configurable rate and bounded by a maximum penalty cap.
    3. Fresher Protection: Prevents harsh deductions on entry-level/internship roles,
       ensuring strong candidates with little formal tenure can remain competitive.
    4. Structured Provenance: Exposes exact numeric gaps, rates, and caps in PenaltyBreakdown.details.
    """

    @classmethod
    def calculate(
        cls,
        jd: Optional[JobDescription],
        resume: Optional[Resume],
        config: Optional[RankingConfig] = None,
        kw_breakdown: Optional[Any] = None
    ) -> PenaltyBreakdown:
        """
        Calculates penalty deductions based on structured JD and Resume metadata.
        Returns a populated PenaltyBreakdown.
        """
        cfg = config or DEFAULT_RANKING_CONFIG

        # Extract required experience years from JD safely
        required_years = 0.0
        if jd is not None:
            try:
                raw_req = getattr(jd, "experience_years_required", 0.0)
                required_years = max(0.0, float(raw_req)) if raw_req is not None else 0.0
            except (ValueError, TypeError):
                required_years = 0.0

        # Extract candidate experience years from Resume safely
        candidate_years = 0.0
        if resume is not None:
            try:
                raw_cand = getattr(resume, "experience_years", 0.0)
                candidate_years = max(0.0, float(raw_cand)) if raw_cand is not None else 0.0
            except (ValueError, TypeError):
                candidate_years = 0.0

        # Calculate experience gap
        if required_years <= 0.0:
            experience_gap = 0.0
        else:
            experience_gap = max(0.0, required_years - candidate_years)

        # Compute experience penalty
        rate = max(0.0, float(cfg.experience_penalty_per_year))
        cap = max(0.0, float(cfg.maximum_experience_penalty))

        raw_penalty = experience_gap * rate
        experience_penalty = min(raw_penalty, cap)
        experience_penalty = max(0.0, min(1.0, experience_penalty))

        # Calculate missing critical skill penalty (0.05 per missing required skill)
        missing_critical_penalty = 0.0
        if kw_breakdown and hasattr(kw_breakdown, 'missing_required_skills'):
            num_missing = len(kw_breakdown.missing_required_skills)
            missing_critical_penalty = num_missing * 0.05

        total_penalty = round(experience_penalty + missing_critical_penalty, 4)

        details = {
            "required_years": round(required_years, 2),
            "candidate_years": round(candidate_years, 2),
            "experience_gap_years": round(experience_gap, 2),
            "penalty_rate_per_year": rate,
            "max_penalty_cap": cap,
            "unclamped_experience_penalty": round(raw_penalty, 4),
            "missing_critical_penalty": missing_critical_penalty
        }

        return PenaltyBreakdown(
            experience_penalty=round(experience_penalty, 4),
            missing_critical_penalty=missing_critical_penalty,
            details=details,
            total_penalty=total_penalty
        )
