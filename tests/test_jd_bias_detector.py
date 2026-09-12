import pytest
from app.models import JobDescription, Resume
from app.bias.jd_bias_detector import JDBiasDetector, JDBiasReport
from app.matching.hybrid_ranker import HybridRanker
from app.config import DEFAULT_RANKING_CONFIG


class TestJDBiasDetector:
    def test_clean_job_description(self):
        """Verifies an inclusive, professional JD yields Clean / Low Risk with 0 flags."""
        jd = JobDescription(
            filename="clean_jd.txt",
            raw_text="""
            Job Title: Software Engineer
            About the Role:
            We are looking for a collaborative software engineer with proficiency in Python and PostgreSQL.
            Qualifications:
            - Experience building web services with Python
            - Familiarity with relational database design
            - Degree in Computer Science or equivalent practical experience
            """,
            title="Software Engineer",
            experience_years_required=2.0
        )
        report = JDBiasDetector.analyze(jd)
        assert isinstance(report, JDBiasReport)
        assert report.total_flags == 0
        assert report.overall_risk == "Clean / Low Risk"
        assert len(report.flags) == 0

    def test_pedigree_and_institution_gatekeeping(self):
        """Verifies detection of Tier-1 and specific university pedigree gatekeeping."""
        jd_text = """
        Job Title: Backend Developer
        Requirements:
        - Only candidates from Tier-1 colleges will be considered.
        - IIT only or NIT only graduates preferred.
        - Minimum CGPA 9.2 is strictly required.
        """
        report = JDBiasDetector.analyze_text(jd_text, "Backend Developer", 1.0)
        assert report.total_flags >= 2
        assert report.overall_risk == "High Risk"
        categories = [f.category for f in report.flags]
        assert "Educational Pedigree Gatekeeping" in categories
        assert "Exclusive Institution Requirement" in categories

    def test_corporate_brand_exclusivity(self):
        """Verifies detection of ex-FAANG / big tech brand demands."""
        jd_text = """
        Role: Senior Engineer
        - Must have ex-FAANG experience or worked at tier-1 product companies.
        """
        report = JDBiasDetector.analyze_text(jd_text, "Senior Engineer", 4.0)
        assert report.total_flags >= 1
        assert any("Employer Brand Exclusivity" in f.category for f in report.flags)

    def test_hyper_aggressive_culture_and_unsustainable_hours(self):
        """Verifies detection of buzzwords and non-inclusive culture signals."""
        jd_text = """
        We need a 10x rockstar coding ninja who thrives with 24/7 availability
        and a work hard play hard round-the-clock commitment!
        Must be a native English speaker.
        """
        report = JDBiasDetector.analyze_text(jd_text, "Developer", 2.0)
        assert report.total_flags >= 3
        severities = [f.severity for f in report.flags]
        assert "High" in severities
        # Check suggestions exist
        for f in report.flags:
            assert len(f.suggestion) > 10
            assert len(f.rationale) > 10

    def test_inflated_experience_on_intern_role(self):
        """Verifies flagging unrealistic experience requirements on junior / intern titles."""
        jd = JobDescription(
            filename="intern_jd.txt",
            raw_text="Junior Software Engineering Intern opening at TechCorp.",
            title="Junior Software Engineering Intern",
            experience_years_required=3.0
        )
        report = JDBiasDetector.analyze(jd)
        assert any(f.category == "Inflated Experience Requirement" for f in report.flags)
        flag = next(f for f in report.flags if f.category == "Inflated Experience Requirement")
        assert "0–1 years" in flag.suggestion

    def test_bias_analysis_does_not_modify_candidate_ranking(self):
        """
        CRITICAL INVARIANT: Bias analysis is purely informational and must NOT
        modify candidate scores, keyword matches, semantic scores, or ranking results.
        """
        jd = JobDescription(
            filename="biased_jd.txt",
            raw_text="Job Title: Rockstar Engineer\nMust be an ex-FAANG ninja with 24/7 availability. Required: Python.",
            title="Rockstar Engineer",
            required_skills=["python"],
            experience_years_required=1.0
        )

        res = Resume(
            filename="cand.pdf",
            raw_text="Python software engineer with 2 years experience.",
            candidate_name="Alex Dev",
            skills=["python"],
            experience_years=2.0
        )

        # 1. Rank without bias analysis
        result_pre = HybridRanker.rank(jd, res, DEFAULT_RANKING_CONFIG)
        pre_score = result_pre.final_score

        # 2. Run bias analysis
        report = JDBiasDetector.analyze(jd)
        assert report.total_flags >= 2

        # 3. Rank again
        result_post = HybridRanker.rank(jd, res, DEFAULT_RANKING_CONFIG)
        post_score = result_post.final_score

        # Scores must be strictly identical
        assert pre_score == post_score
        assert result_pre.diagnostics.base_score == result_post.diagnostics.base_score
        assert result_pre.diagnostics.keyword_score == result_post.diagnostics.keyword_score
        assert result_pre.diagnostics.semantic_score == result_post.diagnostics.semantic_score
