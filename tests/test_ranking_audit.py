import pytest
import numpy as np
from app.config import RankingConfig, DEFAULT_RANKING_CONFIG
from app.models import JobDescription, Resume, CandidateResult, ScoreDiagnostics
from app.matching.keyword_matcher import KeywordMatcher
from app.matching.semantic_matcher import SemanticMatcher
from app.matching.penalty_calculator import PenaltyCalculator
from app.matching.hybrid_ranker import HybridRanker
from extraction.jd_extractor import JDExtractor
from extraction.resume_extractor import ResumeExtractor


class TestContributionDiagnostics:
    """Audit and verify machine-readable contribution diagnostics."""

    @pytest.fixture
    def sample_jd(self):
        return JobDescription(
            filename="backend_jd.pdf",
            raw_text="Backend Engineer role",
            title="Backend Engineer",
            required_skills=["python", "fastapi", "postgresql"],
            preferred_skills=["docker"],
            experience_years_required=2.0
        )

    def test_diagnostics_fields_and_identities(self, sample_jd):
        resume = Resume(
            filename="alice.pdf",
            raw_text="Experienced Python backend developer with FastAPI and PostgreSQL.",
            candidate_name="Alice",
            skills=["python", "fastapi", "postgresql"],
            experience_years=1.0,
            sections={"experience": "Developed scalable microservices in Python and FastAPI."}
        )

        res = HybridRanker.rank(sample_jd, resume)

        # Check diagnostics object presence
        diag = res.diagnostics
        assert isinstance(diag, ScoreDiagnostics)
        assert diag.keyword_score == res.keyword_breakdown.score
        assert diag.semantic_score == res.semantic_breakdown.score
        assert diag.keyword_weight == DEFAULT_RANKING_CONFIG.keyword_weight
        assert diag.semantic_weight == DEFAULT_RANKING_CONFIG.semantic_weight

        # Check mathematical identities
        expected_kw_contrib = round(diag.keyword_score * diag.keyword_weight, 4)
        expected_sem_contrib = round(diag.semantic_score * diag.semantic_weight, 4)
        assert diag.keyword_contribution == expected_kw_contrib
        assert diag.semantic_contribution == expected_sem_contrib

        expected_base = round(expected_kw_contrib + expected_sem_contrib, 4)
        assert diag.base_score == expected_base

        expected_final = round(max(0.0, min(1.0, expected_base - diag.total_penalty)), 4)
        assert diag.final_score == expected_final
        assert res.final_score == expected_final

        # Check serialization in to_dict()
        d = res.to_dict()
        assert "diagnostics" in d
        assert "base_score" in d
        assert d["diagnostics"]["keyword_contribution"] == expected_kw_contrib
        assert d["diagnostics"]["semantic_contribution"] == expected_sem_contrib
        assert d["diagnostics"]["base_score"] == expected_base
        assert d["diagnostics"]["final_score"] == expected_final


class TestKeywordSemanticIndependence:
    """
    Adversarially proves all four quadrant cases:
    Case A: Strong keyword + strong semantic
    Case B: Strong keyword + weak semantic (anti-skill-stuffing)
    Case C: Weak keyword + strong semantic (paraphrase recognition)
    Case D: Weak keyword + weak semantic (unrelated domain)
    """

    @pytest.fixture
    def jd(self):
        text = """
        Job Title: Senior Backend Engineer
        Requirements:
        Must have experience with Python, FastAPI, and PostgreSQL.
        Preferred:
        Experience with Docker and AWS is a plus.
        """
        return JDExtractor.parse_jd("backend.pdf", text)

    def test_quadrant_cases_a_b_c_d(self, jd):
        # Case A: Strong keyword + strong semantic
        res_a_text = """
        Alice Senior Backend
        Skills: Python, FastAPI, PostgreSQL, Docker, AWS
        Experience:
        Architected high-throughput REST APIs and asynchronous microservices using FastAPI.
        Designed relational database schemas and optimized PostgreSQL query execution.
        Containerized services using Docker and deployed on AWS ECS infrastructure.
        """
        resume_a = ResumeExtractor.parse_resume("cand_a.pdf", res_a_text)
        resume_a.experience_years = 3.0

        # Case B: Strong keyword + weak semantic (Skill stuffing)
        res_b_text = """
        Bob Skill Stuffer
        Skills: Python, FastAPI, PostgreSQL, Docker, AWS
        Experience:
        Worked as a retail cashier managing store transactions, customer inquiries,
        and weekly inventory audits at a department store.
        """
        resume_b = ResumeExtractor.parse_resume("cand_b.pdf", res_b_text)
        resume_b.experience_years = 3.0

        # Case C: Weak keyword + strong semantic (Paraphrased backend)
        res_c_text = """
        Charlie Paraphrased
        Skills: Go
        Experience:
        Architected high-throughput REST APIs and asynchronous microservices.
        Designed relational database schemas, complex joins, and optimized query execution.
        Containerized distributed services and deployed on public cloud infrastructure.
        """
        resume_c = ResumeExtractor.parse_resume("cand_c.pdf", res_c_text)
        resume_c.experience_years = 3.0

        # Case D: Weak keyword + weak semantic (Unrelated domain)
        res_d_text = """
        David Pastry Chef
        Skills: Baking, Culinary Arts
        Experience:
        Prepared French pastries, sourdough bread, and seasonal dessert menus.
        Managed kitchen inventory, food hygiene standards, and pastry presentation.
        """
        resume_d = ResumeExtractor.parse_resume("cand_d.pdf", res_d_text)
        resume_d.experience_years = 3.0

        result_a = HybridRanker.rank(jd, resume_a)
        result_b = HybridRanker.rank(jd, resume_b)
        result_c = HybridRanker.rank(jd, resume_c)
        result_d = HybridRanker.rank(jd, resume_d)

        # Assert Case A: High keyword & high semantic & highest final
        assert result_a.keyword_breakdown.score == 1.0
        assert result_a.semantic_breakdown.score > 0.40
        assert result_a.final_score > 0.60

        # Assert Case B: High keyword (1.0) but low semantic
        assert result_b.keyword_breakdown.score == 1.0
        assert result_b.semantic_breakdown.score < result_a.semantic_breakdown.score
        # Case B final score is materially lower than Case A
        assert result_a.final_score > result_b.final_score

        # Assert Case C: Zero/low keyword but strong semantic
        assert result_c.keyword_breakdown.score == 0.0
        assert result_c.semantic_breakdown.score >= 0.25
        # Receives meaningful credit despite zero brand keywords
        assert result_c.final_score >= 0.15

        # Assert Case D: Zero keyword and zero/negligible semantic
        assert result_d.keyword_breakdown.score == 0.0
        assert result_d.semantic_breakdown.score <= 0.05
        assert result_d.final_score <= 0.05

        # Strict ordering: Case A > Case B and Case C > Case D
        assert result_a.final_score > result_b.final_score > result_d.final_score
        assert result_c.final_score > result_d.final_score


class TestRequiredSkillDominance:
    """Verifies that preferred skill matches cannot overwhelm missing core requirements."""

    def test_required_dominates_preferred(self):
        jd = JobDescription(
            filename="jd_dom.pdf",
            raw_text="Required: Python, FastAPI. Preferred: Kubernetes, Docker, Redis.",
            required_skills=["python", "fastapi"],
            preferred_skills=["kubernetes", "docker", "redis"]
        )

        # Candidate 1: Has 2/2 required skills, 0 preferred
        res_req = Resume(
            filename="res_req.pdf",
            raw_text="Skills: Python, FastAPI",
            skills=["python", "fastapi"]
        )

        # Candidate 2: Has 0/2 required skills, 3/3 preferred
        res_pref = Resume(
            filename="res_pref.pdf",
            raw_text="Skills: Kubernetes, Docker, Redis",
            skills=["kubernetes", "docker", "redis"]
        )

        rank_req = HybridRanker.rank(jd, res_req)
        rank_pref = HybridRanker.rank(jd, res_pref)

        # In keyword breakdown, required weight is 0.70 vs preferred 0.30
        assert rank_req.keyword_breakdown.score >= 0.70
        assert rank_pref.keyword_breakdown.score <= 0.30
        assert rank_req.final_score > rank_pref.final_score


class TestSemanticNoiseMatrix:
    """Verifies sentence transformer similarity distribution across semantic categories."""

    def test_semantic_noise_matrix_distribution(self):
        jd_text = "Develop backend REST APIs in Python using PostgreSQL databases."

        clearly_relevant = [
            "Built HTTP services and backend endpoints in Python.",
            "Designed relational schemas and queries in PostgreSQL."
        ]

        related_weaker = [
            "Automated software integration tests using pytest and bash scripts.",
            "Full stack web development using React and Node.js."
        ]

        clearly_unrelated = [
            "Prepared French pastries and croissants in an artisan bakery.",
            "Executed email marketing campaigns and social media advertisements.",
            "Managed corporate payroll and executive travel arrangements."
        ]

        embedder = SemanticMatcher.get_embedding_model()
        jd_vec = embedder.encode(jd_text, convert_to_numpy=True)
        jd_norm = jd_vec / np.linalg.norm(jd_vec)

        # 1. Clearly relevant similarities (>= 0.40)
        for text in clearly_relevant:
            vec = embedder.encode(text, convert_to_numpy=True)
            sim = float(np.dot(jd_norm, vec / np.linalg.norm(vec)))
            assert sim >= 0.40, f"Relevant pair '{text}' produced unexpectedly low sim {sim}"

        # 2. Related weaker similarities (0.20 to 0.40)
        for text in related_weaker:
            vec = embedder.encode(text, convert_to_numpy=True)
            sim = float(np.dot(jd_norm, vec / np.linalg.norm(vec)))
            assert 0.20 <= sim < 0.40, f"Weaker pair '{text}' produced unexpected sim {sim}"

        # 3. Clearly unrelated similarities must be below or near the noise threshold (<= 0.18)
        for text in clearly_unrelated:
            vec = embedder.encode(text, convert_to_numpy=True)
            sim = float(np.dot(jd_norm, vec / np.linalg.norm(vec)))
            assert sim <= 0.18, f"Unrelated pair '{text}' produced high similarity {sim}"


class TestExperiencePenaltyBoundaries:
    """Stress-tests experience penalty calculations and fresher protection."""

    def test_experience_penalty_scenarios(self):
        # 1. No experience requirement -> penalty 0.0
        jd_no_req = JobDescription(filename="j0.pdf", raw_text="", experience_years_required=0.0)
        res_0 = Resume(filename="r0.pdf", raw_text="", experience_years=0.0)
        p0 = PenaltyCalculator.calculate(jd_no_req, res_0)
        assert p0.total_penalty == 0.0

        # 2. Candidate exceeds requirement -> penalty 0.0
        jd_2 = JobDescription(filename="j2.pdf", raw_text="", experience_years_required=2.0)
        res_4 = Resume(filename="r4.pdf", raw_text="", experience_years=4.0)
        p_exceeds = PenaltyCalculator.calculate(jd_2, res_4)
        assert p_exceeds.total_penalty == 0.0

        # 3. Candidate exactly meets requirement -> penalty 0.0
        res_2 = Resume(filename="r2.pdf", raw_text="", experience_years=2.0)
        p_meets = PenaltyCalculator.calculate(jd_2, res_2)
        assert p_meets.total_penalty == 0.0

        # 4. Candidate slightly below (1 year gap) -> 0.05
        res_1 = Resume(filename="r1.pdf", raw_text="", experience_years=1.0)
        p_slight = PenaltyCalculator.calculate(jd_2, res_1)
        assert p_slight.total_penalty == 0.05

        # 5. Candidate substantially below (5 years gap) -> capped at 0.20
        jd_5 = JobDescription(filename="j5.pdf", raw_text="", experience_years_required=5.0)
        p_substantial = PenaltyCalculator.calculate(jd_5, res_0)
        assert p_substantial.total_penalty == 0.20

    def test_fresher_retention_against_experienced_mediocre(self):
        """Proves that a strong fresher with 0 yrs exp is not unfairly reversed by a mediocre experienced candidate."""
        jd = JobDescription(
            filename="jd.pdf",
            raw_text="Role requiring Python backend",
            required_skills=["python", "fastapi", "postgresql"],
            experience_years_required=2.0
        )

        # Candidate A: Exceptional skills (1.0), 0 years exp (gap 2 yrs -> 0.10 penalty)
        cand_a = Resume(
            filename="fresher.pdf",
            raw_text="Python FastAPI PostgreSQL backend developer with deep open source projects.",
            candidate_name="Strong Fresher",
            skills=["python", "fastapi", "postgresql"],
            experience_years=0.0,
            sections={"experience": "Developed scalable microservices in Python and FastAPI with PostgreSQL databases."}
        )

        # Candidate B: Mediocre skills (1/3 req), 2 years exp (0 penalty)
        cand_b = Resume(
            filename="senior.pdf",
            raw_text="Software engineer with general coding experience.",
            candidate_name="Mediocre Experienced",
            skills=["python"],
            experience_years=2.0,
            sections={"experience": "Maintained legacy software and attended daily standups."}
        )

        res_a = HybridRanker.rank(jd, cand_a)
        res_b = HybridRanker.rank(jd, cand_b)

        # Candidate A incurs 0.10 penalty but has far superior keyword and semantic scores
        assert res_a.penalties.total_penalty == 0.10
        assert res_b.penalties.total_penalty == 0.0
        assert res_a.final_score > res_b.final_score, "Strong fresher should rank above mediocre experienced candidate"


class TestScoreMonotonicity:
    """Verifies intuitive monotonic properties of the scoring function."""

    @pytest.fixture
    def jd(self):
        return JobDescription(
            filename="jd.pdf",
            raw_text="Role",
            required_skills=["python", "fastapi", "postgresql"],
            experience_years_required=2.0
        )

    def test_skill_addition_monotonicity(self, jd):
        res_fewer = Resume(filename="r1.pdf", raw_text="", skills=["python"])
        res_more = Resume(filename="r2.pdf", raw_text="", skills=["python", "fastapi"])

        kw_fewer = KeywordMatcher.match(jd, res_fewer)
        kw_more = KeywordMatcher.match(jd, res_more)
        assert kw_more.keyword_score >= kw_fewer.keyword_score

    def test_experience_addition_monotonicity(self, jd):
        res_less_exp = Resume(filename="r1.pdf", raw_text="", skills=["python"], experience_years=0.5)
        res_more_exp = Resume(filename="r2.pdf", raw_text="", skills=["python"], experience_years=2.0)

        pen_less = PenaltyCalculator.calculate(jd, res_less_exp)
        pen_more = PenaltyCalculator.calculate(jd, res_more_exp)
        assert pen_more.total_penalty <= pen_less.total_penalty


class TestCandidateOrderIndependence:
    """Proves scores are 100% candidate-independent."""

    def test_batch_and_single_candidate_independence(self):
        jd = JobDescription(
            filename="jd.pdf",
            raw_text="Python role",
            required_skills=["python", "postgresql"],
            experience_years_required=1.0
        )
        c1 = Resume(filename="c1.pdf", raw_text="Python dev", skills=["python"], experience_years=1.0)
        c2 = Resume(filename="c2.pdf", raw_text="PostgreSQL dev", skills=["postgresql"], experience_years=0.0)
        c3 = Resume(filename="c3.pdf", raw_text="Java dev", skills=["java"], experience_years=3.0)

        # Order 1
        batch_1 = HybridRanker.rank_batch(jd, [c1, c2, c3])
        scores_1 = {r.resume.filename: r.final_score for r in batch_1}

        # Order 2
        batch_2 = HybridRanker.rank_batch(jd, [c3, c1, c2])
        scores_2 = {r.resume.filename: r.final_score for r in batch_2}

        # Single evaluation
        single_c1 = HybridRanker.rank(jd, c1)

        assert scores_1["c1.pdf"] == scores_2["c1.pdf"] == single_c1.final_score
        assert scores_1["c2.pdf"] == scores_2["c2.pdf"]
        assert scores_1["c3.pdf"] == scores_2["c3.pdf"]


class TestRankingDeterminismAndBounds:
    """Verifies score boundedness in [0.0, 1.0] and ranking stability across repetitions."""

    def test_deterministic_repetition(self):
        jd = JobDescription(
            filename="jd.pdf",
            raw_text="Python FastAPI PostgreSQL",
            required_skills=["python", "fastapi"],
            preferred_skills=["docker"],
            experience_years_required=2.0
        )
        candidates = [
            Resume(filename=f"c{i}.pdf", raw_text=f"Skills: python {i}", skills=["python"], experience_years=float(i % 3))
            for i in range(5)
        ]

        run_1 = HybridRanker.rank_batch(jd, candidates)
        run_2 = HybridRanker.rank_batch(jd, candidates)

        for r1, r2 in zip(run_1, run_2):
            assert r1.resume.filename == r2.resume.filename
            assert r1.final_score == r2.final_score
            assert 0.0 <= r1.final_score <= 1.0
            assert 0.0 <= r1.keyword_score <= 1.0
            assert 0.0 <= r1.semantic_score <= 1.0
            assert 0.0 <= r1.penalties.total_penalty <= 1.0
