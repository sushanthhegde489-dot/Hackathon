import pytest
from app.models import (
    JobDescription, Resume, CandidateResult, KeywordScoreBreakdown,
    SemanticScoreBreakdown, PenaltyBreakdown, ScoreDiagnostics
)
from app.qa.recruiter_qa import RecruiterQAEngine, QAResponse


@pytest.fixture
def sample_qa_setup():
    jd = JobDescription(
        filename="test_jd.pdf",
        raw_text="Backend Engineer Job Description",
        title="Backend Software Engineer",
        required_skills=["python", "postgresql", "fastapi", "docker"],
        preferred_skills=["aws", "redis"],
        experience_years_required=2.0
    )

    # Candidate 1: Top Candidate (#1)
    c1 = CandidateResult(
        resume=Resume(
            filename="cand_alice.pdf",
            raw_text="Alice's resume",
            candidate_name="Alice Senior",
            experience_years=3.0,
            skills=["python", "postgresql", "fastapi", "docker", "aws"]
        ),
        keyword_breakdown=KeywordScoreBreakdown(
            score=0.90,
            required_skill_score=1.0,
            preferred_skill_score=0.5,
            matched_required_skills=["python", "postgresql", "fastapi", "docker"],
            missing_required_skills=[],
            matched_preferred_skills=["aws"],
            missing_preferred_skills=["redis"]
        ),
        semantic_breakdown=SemanticScoreBreakdown(
            score=0.82,
            strongest_matches=[{"resume_section": "experience", "similarity": 0.85, "resume_snippet": "Architected distributed FastAPI microservices."}]
        ),
        penalties=PenaltyBreakdown(total_penalty=0.0),
        diagnostics=ScoreDiagnostics(
            keyword_score=0.90, keyword_weight=0.40, keyword_contribution=0.360,
            semantic_score=0.82, semantic_weight=0.60, semantic_contribution=0.492,
            base_score=0.852, final_score=0.852
        ),
        final_score=0.852,
        rank=1,
        ranking_reason="Matched all required skills with strong semantic alignment."
    )

    # Candidate 2: Close Runner-up (#2)
    c2 = CandidateResult(
        resume=Resume(
            filename="cand_bob.pdf",
            raw_text="Bob's resume",
            candidate_name="Bob Junior",
            experience_years=2.0,
            skills=["python", "postgresql", "docker"]
        ),
        keyword_breakdown=KeywordScoreBreakdown(
            score=0.70,
            required_skill_score=0.75,
            preferred_skill_score=0.0,
            matched_required_skills=["python", "postgresql", "docker"],
            missing_required_skills=["fastapi"],
            matched_preferred_skills=[],
            missing_preferred_skills=["aws", "redis"]
        ),
        semantic_breakdown=SemanticScoreBreakdown(
            score=0.74,
            strongest_matches=[{"resume_section": "projects", "similarity": 0.77, "resume_snippet": "Built Dockerized PostgreSQL services."}]
        ),
        penalties=PenaltyBreakdown(total_penalty=0.0),
        diagnostics=ScoreDiagnostics(
            keyword_score=0.70, keyword_weight=0.40, keyword_contribution=0.280,
            semantic_score=0.74, semantic_weight=0.60, semantic_contribution=0.444,
            base_score=0.724, final_score=0.724
        ),
        final_score=0.724,
        rank=2,
        ranking_reason="Strong match but missing FastAPI."
    )

    # Candidate 3: Bronze (#3)
    c3 = CandidateResult(
        resume=Resume(
            filename="cand_charlie.pdf",
            raw_text="Charlie's resume",
            candidate_name="Charlie Mid",
            experience_years=2.0,
            skills=["python", "fastapi"]
        ),
        keyword_breakdown=KeywordScoreBreakdown(
            score=0.55,
            matched_required_skills=["python", "fastapi"],
            missing_required_skills=["postgresql", "docker"]
        ),
        semantic_breakdown=SemanticScoreBreakdown(score=0.68),
        penalties=PenaltyBreakdown(total_penalty=0.0),
        diagnostics=ScoreDiagnostics(
            keyword_score=0.55, keyword_weight=0.40, keyword_contribution=0.220,
            semantic_score=0.68, semantic_weight=0.60, semantic_contribution=0.408,
            base_score=0.628, final_score=0.628
        ),
        final_score=0.628,
        rank=3,
        ranking_reason="Solid Python experience."
    )

    # Candidate 4: Outside Top 3 (#4) with Penalty
    c4 = CandidateResult(
        resume=Resume(
            filename="cand_david.pdf",
            raw_text="David's resume",
            candidate_name="David Fresher",
            experience_years=1.0,
            skills=["python"]
        ),
        keyword_breakdown=KeywordScoreBreakdown(
            score=0.35,
            required_skill_score=0.25,
            matched_required_skills=["python"],
            missing_required_skills=["postgresql", "fastapi", "docker"]
        ),
        semantic_breakdown=SemanticScoreBreakdown(score=0.58),
        penalties=PenaltyBreakdown(
            total_penalty=0.05,
            details={"experience_gap_years": 1.0, "required_years": 2.0, "candidate_years": 1.0}
        ),
        diagnostics=ScoreDiagnostics(
            keyword_score=0.35, keyword_weight=0.40, keyword_contribution=0.140,
            semantic_score=0.58, semantic_weight=0.60, semantic_contribution=0.348,
            base_score=0.488, total_penalty=0.05, final_score=0.438
        ),
        final_score=0.438,
        rank=4,
        ranking_reason="Entry level with experience gap."
    )

    results = [c1, c2, c3, c4]
    engine = RecruiterQAEngine(results, jd)
    return engine, jd, results


class TestRecruiterQAEngine:
    def test_comparative_query_exact_values(self, sample_qa_setup):
        """Verifies comparative question compares exact scores, skills, and penalties."""
        engine, jd, results = sample_qa_setup
        resp = engine.answer_query("Why did Alice Senior rank above Bob Junior?")
        assert resp.intent == "comparison"
        assert "Alice Senior" in resp.answer
        assert "Bob Junior" in resp.answer
        assert "85.2%" in resp.answer
        assert "72.4%" in resp.answer
        assert "fastapi" in resp.answer.lower()

    def test_comparative_query_by_ranks(self, sample_qa_setup):
        """Verifies comparative query resolves #1 vs #2 cleanly."""
        engine, jd, results = sample_qa_setup
        resp = engine.answer_query("Compare #1 and #4")
        assert resp.intent == "comparison"
        assert "Alice Senior" in resp.answer
        assert "David Fresher" in resp.answer
        assert "Experience Deduction" in resp.answer

    def test_why_not_top3_query(self, sample_qa_setup):
        """Verifies why candidate X is not in top 3 correctly contrasts with #3 threshold."""
        engine, jd, results = sample_qa_setup
        resp = engine.answer_query("Why is David Fresher not in the top 3?")
        assert resp.intent == "rank_why"
        assert "David Fresher" in resp.answer
        assert "Missing critical required skill" in resp.answer
        assert "experience deduction" in resp.answer.lower()

    def test_missing_skill_query(self, sample_qa_setup):
        """Verifies detection of candidates missing a specific skill."""
        engine, jd, results = sample_qa_setup
        resp = engine.answer_query("Which candidates are missing FastAPI?")
        assert resp.intent == "missing_skill"
        assert "Fastapi" in resp.answer or "fastapi" in resp.answer.lower()
        # Bob Junior and David Fresher miss FastAPI
        assert "Bob Junior" in resp.answer

    def test_has_skill_query(self, sample_qa_setup):
        """Verifies finding candidates who possess a specific skill."""
        engine, jd, results = sample_qa_setup
        resp = engine.answer_query("Who has Docker?")
        assert resp.intent == "has_skill"
        assert "Alice Senior" in resp.answer
        assert "Bob Junior" in resp.answer

    def test_no_penalty_query(self, sample_qa_setup):
        """Verifies listing candidates with zero experience penalty."""
        engine, jd, results = sample_qa_setup
        resp = engine.answer_query("Which candidates have no experience penalty?")
        assert resp.intent == "no_penalty"
        assert "Alice Senior" in resp.answer
        assert "Bob Junior" in resp.answer
        assert "Charlie Mid" in resp.answer
        assert "David Fresher" not in resp.answer

    def test_penalty_reasons_query(self, sample_qa_setup):
        """Verifies explanation of penalty for a penalized candidate."""
        engine, jd, results = sample_qa_setup
        resp = engine.answer_query("Why did David Fresher lose points?")
        assert resp.intent == "penalty_reasons"
        assert "David Fresher" in resp.answer
        assert "-0.0500" in resp.answer or "1.0 years" in resp.answer

    def test_semantic_standouts_query(self, sample_qa_setup):
        """Verifies highlighting candidates with top semantic scores."""
        engine, jd, results = sample_qa_setup
        resp = engine.answer_query("Who has the strongest semantic alignment?")
        assert resp.intent == "semantic_standouts"
        assert "Alice Senior" in resp.answer

    def test_suggested_questions(self, sample_qa_setup):
        """Verifies suggested questions are non-empty and mention current candidates."""
        engine, jd, results = sample_qa_setup
        suggestions = engine.get_suggested_questions()
        assert len(suggestions) >= 4
        assert any("Alice Senior" in s for s in suggestions)
