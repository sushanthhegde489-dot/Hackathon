import pytest
from app.config import RankingConfig
from app.models import JobDescription, Resume, PenaltyBreakdown
from app.matching.penalty_calculator import PenaltyCalculator


class TestPenaltyCalculator:
    """Verifies experience gap and penalty calculation rules."""

    def test_no_experience_requirement(self):
        """When JD requires 0 years, penalty is strictly 0.0."""
        jd = JobDescription(filename="intern_jd.txt", raw_text="", experience_years_required=0.0)
        resume = Resume(filename="cand.txt", raw_text="", experience_years=0.0)

        pen = PenaltyCalculator.calculate(jd, resume)
        assert pen.experience_penalty == 0.0
        assert pen.total_penalty == 0.0
        assert pen.details["experience_gap_years"] == 0.0

    def test_candidate_meets_requirement(self):
        """When candidate meets the required years, penalty is 0.0."""
        jd = JobDescription(filename="jd.txt", raw_text="", experience_years_required=2.0)
        resume = Resume(filename="cand.txt", raw_text="", experience_years=2.0)

        pen = PenaltyCalculator.calculate(jd, resume)
        assert pen.experience_penalty == 0.0
        assert pen.total_penalty == 0.0
        assert pen.details["experience_gap_years"] == 0.0

    def test_candidate_exceeds_requirement(self):
        """When candidate has more experience than required, penalty is strictly 0.0 (no negative penalty)."""
        jd = JobDescription(filename="jd.txt", raw_text="", experience_years_required=2.0)
        resume = Resume(filename="cand.txt", raw_text="", experience_years=5.5)

        pen = PenaltyCalculator.calculate(jd, resume)
        assert pen.experience_penalty == 0.0
        assert pen.total_penalty == 0.0
        assert pen.details["experience_gap_years"] == 0.0

    def test_small_experience_gap(self):
        """Gap of 1 year incurs penalty = 1.0 * rate (default 0.05)."""
        jd = JobDescription(filename="jd.txt", raw_text="", experience_years_required=2.0)
        resume = Resume(filename="cand.txt", raw_text="", experience_years=1.0)

        pen = PenaltyCalculator.calculate(jd, resume)
        assert pen.experience_penalty == 0.05
        assert pen.total_penalty == 0.05
        assert pen.details["experience_gap_years"] == 1.0
        assert pen.details["penalty_rate_per_year"] == 0.05

    def test_large_experience_gap_and_maximum_cap(self):
        """Large experience gap (e.g. 5 years) is capped at maximum_experience_penalty (default 0.20)."""
        jd = JobDescription(filename="senior_jd.txt", raw_text="", experience_years_required=6.0)
        resume = Resume(filename="fresher.txt", raw_text="", experience_years=0.0)

        pen = PenaltyCalculator.calculate(jd, resume)
        # Raw would be 6 * 0.05 = 0.30, but cap is 0.20
        assert pen.details["unclamped_penalty"] == 0.30
        assert pen.experience_penalty == 0.20
        assert pen.total_penalty == 0.20

    def test_configurable_penalty_rate_and_cap(self):
        """Custom configuration allows adjusting penalty rate and cap."""
        custom_cfg = RankingConfig(
            experience_penalty_per_year=0.08,
            maximum_experience_penalty=0.15
        )
        jd = JobDescription(filename="jd.txt", raw_text="", experience_years_required=3.0)
        resume = Resume(filename="cand.txt", raw_text="", experience_years=1.0)

        # Gap = 2.0 years. Raw = 2.0 * 0.08 = 0.16. Cap is 0.15.
        pen = PenaltyCalculator.calculate(jd, resume, config=custom_cfg)
        assert pen.details["experience_gap_years"] == 2.0
        assert pen.details["penalty_rate_per_year"] == 0.08
        assert pen.experience_penalty == 0.15
        assert pen.total_penalty == 0.15

    def test_internship_and_fresher_behavior(self):
        """For entry-level roles (0-1 yrs), penalty remains minor, allowing competitive ranking."""
        jd = JobDescription(filename="intern_jd.txt", raw_text="", experience_years_required=1.0)
        fresher = Resume(filename="fresher.txt", raw_text="", experience_years=0.0)

        pen = PenaltyCalculator.calculate(jd, fresher)
        # 1 year gap = 0.05 deduction
        assert pen.total_penalty == 0.05
        assert pen.total_penalty < 0.10

    def test_edge_cases_and_malformed_inputs(self):
        """Handles None objects, negative experience, and missing attributes gracefully."""
        # None inputs
        pen_none = PenaltyCalculator.calculate(None, None)
        assert pen_none.total_penalty == 0.0

        # Negative experience in JD
        jd_neg = JobDescription(filename="jd.txt", raw_text="", experience_years_required=-3.0)
        resume = Resume(filename="cand.txt", raw_text="", experience_years=1.0)
        pen_neg_jd = PenaltyCalculator.calculate(jd_neg, resume)
        assert pen_neg_jd.total_penalty == 0.0

        # Negative experience in Resume (clamped to 0.0)
        jd_pos = JobDescription(filename="jd.txt", raw_text="", experience_years_required=2.0)
        resume_neg = Resume(filename="cand.txt", raw_text="", experience_years=-1.0)
        pen_neg_res = PenaltyCalculator.calculate(jd_pos, resume_neg)
        assert pen_neg_res.details["experience_gap_years"] == 2.0
        assert pen_neg_res.total_penalty == 0.10

        # Details structure
        assert "required_years" in pen_neg_res.details
        assert "candidate_years" in pen_neg_res.details
        assert "max_penalty_cap" in pen_neg_res.details
