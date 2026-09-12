import pytest
import numpy as np
from app.config import RankingConfig
from app.models import JobDescription, Resume, ExperienceEntry, ProjectEntry, CandidateResult
from app.matching.hybrid_ranker import HybridRanker
from extraction.jd_extractor import JDExtractor
from extraction.resume_extractor import ResumeExtractor


@pytest.fixture(scope="module")
def intern_jd():
    return JobDescription(
        filename="swe_intern_jd.txt",
        title="Software Engineering Intern",
        experience_years_required=1.0,
        required_skills=["python", "postgresql"],
        preferred_skills=["docker"],
        raw_text="""Software Engineering Intern
Required:
Develop backend microservices and APIs using Python.
Design and query relational databases with PostgreSQL.
Experience: At least 1 year of experience.
Preferred:
Docker and container deployment experience.
Responsibilities:
Collaborate with engineering teams to build scalable web applications.""",
        sections={
            "required": "Develop backend microservices and APIs using Python.\nDesign and query relational databases with PostgreSQL.",
            "preferred": "Docker and container deployment experience.",
            "contextual": "Collaborate with engineering teams to build scalable web applications."
        }
    )


class TestHybridRankerFormulas:
    """Verifies hybrid score calculation formulas and weighting."""

    def test_combined_contribution_with_default_weights(self, intern_jd):
        resume = Resume(
            filename="cand_backend.txt",
            candidate_name="Alice Backend",
            skills=["python", "postgresql", "docker"],
            experience_years=1.0,
            raw_text="Built Python microservices and PostgreSQL schemas. Worked with Docker deployments.",
            sections={
                "experience": "Built Python microservices and PostgreSQL schemas.\nWorked with Docker deployments."
            }
        )

        res = HybridRanker.rank(intern_jd, resume)

        # Keyword: 1.0 req * 0.70 + 1.0 pref * 0.30 = 1.0000
        assert res.keyword_score == 1.0
        assert res.semantic_score > 0.35
        assert res.penalties.total_penalty == 0.0  # Meets 1.0 yr requirement

        expected_base = (res.keyword_score * 0.40) + (res.semantic_score * 0.60)
        assert abs(res.final_score - round(expected_base, 4)) < 1e-4
        assert 0.0 <= res.final_score <= 1.0

    def test_keyword_only_contribution(self, intern_jd):
        cfg = RankingConfig(keyword_weight=1.0, semantic_weight=0.0)
        resume = Resume(
            filename="cand.txt",
            skills=["python", "postgresql"],
            experience_years=1.0,
            raw_text="Python and PostgreSQL.",
            sections={"experience": "Python and PostgreSQL."}
        )

        res = HybridRanker.rank(intern_jd, resume, config=cfg)
        # Required skills matched: 1.0 * 0.70 = 0.70. Preferred: 0.0. Keyword score: 0.70
        assert res.keyword_score == 0.70
        assert res.final_score == 0.70

    def test_semantic_only_contribution(self, intern_jd):
        cfg = RankingConfig(keyword_weight=0.0, semantic_weight=1.0)
        resume = Resume(
            filename="cand.txt",
            skills=[],  # Zero keyword credit
            experience_years=1.0,
            raw_text="Built HTTP web services and relational data models.",
            sections={"experience": "Built HTTP web services and relational data models."}
        )

        res = HybridRanker.rank(intern_jd, resume, config=cfg)
        assert res.keyword_score == 0.0
        assert res.semantic_score > 0.15
        assert res.final_score == round(max(0.0, res.semantic_score - res.penalties.total_penalty), 4)

    def test_penalty_subtraction(self, intern_jd):
        # Candidate has 0 years experience against 1.0 year requirement -> 0.05 penalty
        resume_fresher = Resume(
            filename="fresher.txt",
            skills=["python", "postgresql", "docker"],
            experience_years=0.0,
            raw_text="Built Python microservices and PostgreSQL schemas.",
            sections={"experience": "Built Python microservices and PostgreSQL schemas."}
        )

        res = HybridRanker.rank(intern_jd, resume_fresher)
        assert res.penalties.total_penalty == 0.05
        base = (res.keyword_score * 0.40) + (res.semantic_score * 0.60)
        assert res.final_score == round(max(0.0, base - 0.05), 4)

    def test_zero_and_perfect_score_boundaries(self):
        jd = JobDescription(
            filename="jd.txt",
            required_skills=["python"],
            experience_years_required=0.0,
            raw_text="Required: Python developer.",
            sections={"required": "Python developer."}
        )

        # Zero match
        unrelated = Resume(
            filename="chef.txt",
            skills=[],
            experience_years=0.0,
            raw_text="Bakery chef making artisan pastries.",
            sections={"experience": "Bakery chef making artisan pastries."}
        )
        res_zero = HybridRanker.rank(jd, unrelated)
        assert res_zero.final_score < 0.05
        assert res_zero.final_score >= 0.0

        # Perfect match candidate with identical wording
        perfect = Resume(
            filename="perfect.txt",
            skills=["python"],
            experience_years=0.0,
            raw_text="Python developer.",
            sections={"required": "Python developer."}
        )
        res_perf = HybridRanker.rank(jd, perfect)
        assert res_perf.keyword_score == 0.70  # 1.0 req * 0.70 weight
        assert res_perf.final_score > 0.60


class TestHybridRankerConfigValidation:
    """Verifies that invalid configuration weights fail fast and clearly."""

    def test_weights_must_sum_to_one(self):
        invalid_cfg = RankingConfig(keyword_weight=0.50, semantic_weight=0.60)
        with pytest.raises(ValueError, match="must sum to 1.0"):
            invalid_cfg.validate()

    def test_negative_weights_disallowed(self):
        invalid_cfg = RankingConfig(keyword_weight=-0.20, semantic_weight=1.20)
        with pytest.raises(ValueError, match="non-negative"):
            invalid_cfg.validate()

    def test_negative_penalty_parameters_disallowed(self):
        invalid_cfg = RankingConfig(experience_penalty_per_year=-0.05)
        with pytest.raises(ValueError, match="non-negative"):
            invalid_cfg.validate()


class TestCandidateIndependenceAndDeterminism:
    """Verifies candidate independence and deterministic tie-breaking."""

    def test_candidate_independence_single_vs_batch(self, intern_jd):
        cand_a = Resume(
            filename="a_cand.txt",
            candidate_name="Alice",
            skills=["python"],
            experience_years=1.0,
            raw_text="Python developer."
        )
        cand_b = Resume(
            filename="b_cand.txt",
            candidate_name="Bob",
            skills=["docker"],
            experience_years=0.0,
            raw_text="Docker specialist."
        )
        cand_c = Resume(
            filename="c_cand.txt",
            candidate_name="Charlie",
            skills=[],
            experience_years=0.0,
            raw_text="Marketing intern."
        )

        single_a = HybridRanker.rank(intern_jd, cand_a)
        batch_res = HybridRanker.rank_batch(intern_jd, [cand_b, cand_a, cand_c])

        cand_a_in_batch = next(r for r in batch_res if r.resume.filename == "a_cand.txt")

        # Invariant: Score components must be identical
        assert single_a.keyword_score == cand_a_in_batch.keyword_score
        assert single_a.semantic_score == cand_a_in_batch.semantic_score
        assert single_a.penalties.total_penalty == cand_a_in_batch.penalties.total_penalty
        assert single_a.final_score == cand_a_in_batch.final_score

    def test_deterministic_tie_breaking_by_filename(self):
        jd = JobDescription(filename="jd.txt", raw_text="Required: Python.", required_skills=["python"])
        cand_z = Resume(filename="z_candidate.txt", candidate_name="Same", skills=["python"], raw_text="Python.")
        cand_a = Resume(filename="a_candidate.txt", candidate_name="Same", skills=["python"], raw_text="Python.")

        batch_1 = HybridRanker.rank_batch(jd, [cand_z, cand_a])
        batch_2 = HybridRanker.rank_batch(jd, [cand_a, cand_z])

        # Exactly tied scores must sort alphabetically by filename
        assert batch_1[0].resume.filename == "a_candidate.txt"
        assert batch_1[1].resume.filename == "z_candidate.txt"
        assert batch_2[0].resume.filename == "a_candidate.txt"
        assert batch_2[1].resume.filename == "z_candidate.txt"


class TestScoreInvariantsAndMonotonicity:
    """Verifies mathematical bounds and monotonicity properties."""

    def test_all_scores_strictly_bounded(self, intern_jd):
        resumes = [
            Resume(filename="r1.txt", skills=["python", "postgresql", "docker"], experience_years=2.0, raw_text="Experienced."),
            Resume(filename="r2.txt", skills=[], experience_years=0.0, raw_text="Unrelated."),
            Resume(filename="r3.txt", skills=["python"], experience_years=0.5, raw_text="Junior.")
        ]
        results = HybridRanker.rank_batch(intern_jd, resumes)
        for r in results:
            assert 0.0 <= r.keyword_score <= 1.0
            assert 0.0 <= r.semantic_score <= 1.0
            assert 0.0 <= r.penalties.total_penalty <= 1.0
            assert 0.0 <= r.final_score <= 1.0

    def test_monotonicity_increasing_experience_does_not_decrease_score(self, intern_jd):
        fresher = Resume(
            filename="fresher.txt",
            skills=["python", "postgresql"],
            experience_years=0.0,
            raw_text="Python and PostgreSQL."
        )
        experienced = Resume(
            filename="exp.txt",
            skills=["python", "postgresql"],
            experience_years=1.5,
            raw_text="Python and PostgreSQL."
        )

        res_fresh = HybridRanker.rank(intern_jd, fresher)
        res_exp = HybridRanker.rank(intern_jd, experienced)

        assert res_exp.final_score >= res_fresh.final_score
        assert res_exp.penalties.total_penalty <= res_fresh.penalties.total_penalty

    def test_monotonicity_adding_preferred_skill_does_not_decrease_score(self, intern_jd):
        base = Resume(filename="b.txt", skills=["python", "postgresql"], raw_text="Backend.")
        plus_pref = Resume(filename="p.txt", skills=["python", "postgresql", "docker"], raw_text="Backend with Docker.")

        res_base = HybridRanker.rank(intern_jd, base)
        res_plus = HybridRanker.rank(intern_jd, plus_pref)

        assert res_plus.keyword_score >= res_base.keyword_score
        assert res_plus.final_score >= res_base.final_score

    def test_monotonicity_removing_required_skill_cannot_increase_score(self, intern_jd):
        full_req = Resume(filename="f.txt", skills=["python", "postgresql"], raw_text="Full req.")
        partial_req = Resume(filename="p.txt", skills=["python"], raw_text="Partial req.")

        res_full = HybridRanker.rank(intern_jd, full_req)
        res_part = HybridRanker.rank(intern_jd, partial_req)

        assert res_full.keyword_score > res_part.keyword_score


class TestAntiKeywordStuffingBehavior:
    """Verifies that repetitive keyword repetition does not defeat hybrid ranking."""

    def test_contextual_experience_beats_keyword_stuffing(self):
        jd = JobDescription(
            filename="jd.txt",
            required_skills=["python", "postgresql", "fastapi"],
            raw_text="""Software Engineer
Required:
Develop backend microservices and REST APIs using Python and FastAPI.
Design and query relational databases with PostgreSQL.""",
            sections={
                "required": "Develop backend microservices and REST APIs using Python and FastAPI.\nDesign and query relational databases with PostgreSQL."
            }
        )

        # Candidate A: Stuffs keywords repeatedly without real context
        stuffed = Resume(
            filename="stuffed.txt",
            candidate_name="Keyword Stuffer",
            skills=["python", "postgresql", "fastapi"],
            raw_text="Python Python Python FastAPI FastAPI PostgreSQL PostgreSQL PostgreSQL.",
            sections={"skills": "Python Python Python FastAPI FastAPI PostgreSQL PostgreSQL PostgreSQL."}
        )

        # Candidate B: Genuine technical experience describing production work
        genuine = Resume(
            filename="genuine.txt",
            candidate_name="Genuine Engineer",
            skills=["python", "postgresql", "fastapi"],
            raw_text="""Experience:
Built Python backend services and scalable REST endpoints using FastAPI.
Designed PostgreSQL schemas, optimized query execution plans, and managed database migrations.""",
            sections={
                "experience": "Built Python backend services and scalable REST endpoints using FastAPI.\nDesigned PostgreSQL schemas, optimized query execution plans, and managed database migrations."
            }
        )

        res_stuffed = HybridRanker.rank(jd, stuffed)
        res_genuine = HybridRanker.rank(jd, genuine)

        # Both get equal keyword credit because both match the 3 canonical skills
        assert res_stuffed.keyword_score == res_genuine.keyword_score

        # Genuine candidate has significantly higher semantic depth
        assert res_genuine.semantic_score > res_stuffed.semantic_score + 0.15

        # Final hybrid score correctly favors the genuine candidate
        assert res_genuine.final_score > res_stuffed.final_score


class TestRankingExplanationProvenance:
    """Verifies that ranking_reason contains true computed values and no hallucinations."""

    def test_ranking_reason_content_and_explainability(self, intern_jd):
        resume = Resume(
            filename="alice.txt",
            candidate_name="Alice Smith",
            skills=["python", "postgresql"],
            experience_years=0.5,
            raw_text="Built Python REST endpoints and PostgreSQL schemas.",
            sections={"experience": "Built Python REST endpoints and PostgreSQL schemas."}
        )

        res = HybridRanker.rank(intern_jd, resume)
        reason = res.ranking_reason

        # Verifies auditable components
        assert "Matched 2/2 required skills (postgresql, python)" in reason
        assert "Experience gap of 0.5 years" in reason
        assert "Final score:" in reason
        assert "Base:" in reason
        assert "Penalty:" in reason


class TestEndToEndPipelineIntegration:
    """Verifies integration from raw text extraction to hybrid ranking."""

    def test_extraction_to_hybrid_ranking(self):
        raw_jd = """Senior Backend Developer
Required:
Strong proficiency in Python.
Experience with PostgreSQL database design.
Minimum 2 years of experience.
Preferred:
Hands-on experience with Docker.
Responsibilities:
Build high-throughput microservices."""

        raw_resume = """Bob Developer
Email: bob@example.com
Experience:
3 years of experience developing backend microservices in Python.
Designed PostgreSQL tables and wrote automated unit tests.
Technologies: Python, PostgreSQL, Docker"""

        # 1. Extraction pipeline
        jd = JDExtractor.parse_jd("backend_jd.txt", raw_jd)
        resume = ResumeExtractor.parse_resume("bob_resume.txt", raw_resume)

        assert "python" in jd.required_skills
        assert jd.experience_years_required == 2.0
        assert resume.experience_years == 3.0

        # 2. Hybrid ranking
        result = HybridRanker.rank(jd, resume)

        assert result.keyword_breakdown.required_skill_score == 1.0  # All required skills matched
        assert result.keyword_score == 0.70
        assert result.penalties.total_penalty == 0.0  # 3.0 yrs exceeds 2.0 yrs
        assert result.semantic_score > 0.35
        assert result.final_score > 0.45


class Test18CandidateComprehensiveEvaluation:
    """
    Evaluates 18 realistic candidates representing the diverse archetypes
    specified in the problem statement.
    """

    def test_18_candidates_hybrid_ranking(self):
        jd = JobDescription(
            filename="swe_backend_jd.txt",
            title="Backend Software Engineer",
            experience_years_required=2.0,
            required_skills=["python", "postgresql", "fastapi"],
            preferred_skills=["docker", "aws"],
            raw_text="""Backend Software Engineer
Required:
Develop robust backend APIs and microservices using Python and FastAPI.
Design relational databases and optimize queries in PostgreSQL.
Experience: At least 2 years of professional software engineering experience.
Preferred:
Docker containerization and AWS cloud infrastructure.
Responsibilities:
Collaborate with agile engineering teams to deliver scalable production software.""",
            sections={
                "required": "Develop robust backend APIs and microservices using Python and FastAPI.\nDesign relational databases and optimize queries in PostgreSQL.",
                "preferred": "Docker containerization and AWS cloud infrastructure.",
                "contextual": "Collaborate with agile engineering teams to deliver scalable production software."
            }
        )

        # 18 Candidate Archetypes
        candidates = [
            # 1. Excellent backend match (all skills + 3 yrs exp)
            Resume(
                filename="01_excellent_backend.txt",
                candidate_name="01 Excellent Backend",
                skills=["python", "fastapi", "postgresql", "docker", "aws"],
                experience_years=3.0,
                raw_text="""Experience:
Built high-throughput FastAPI microservices and REST APIs in Python.
Designed PostgreSQL database architectures and query optimizations.
Deployed Docker containers on AWS cloud infrastructure."""
            ),
            # 2. Strong backend match with less experience (all skills + 0 yrs exp)
            Resume(
                filename="02_fresher_strong_backend.txt",
                candidate_name="02 Fresher Strong Backend",
                skills=["python", "fastapi", "postgresql", "docker"],
                experience_years=0.0,
                raw_text="""Experience:
Developed FastAPI backend services and REST endpoints in Python.
Designed PostgreSQL schemas and wrote automated pytest suites.
Containerized services using Docker."""
            ),
            # 3. Strong skills list but weak semantic experience (keyword stuffed)
            Resume(
                filename="03_stuffed_skills.txt",
                candidate_name="03 Stuffed Skills",
                skills=["python", "fastapi", "postgresql"],
                experience_years=2.0,
                raw_text="""Skills: Python, FastAPI, PostgreSQL
Experience:
Edited configuration files and ran diagnostic tests."""
            ),
            # 4. Strong semantic match but missing explicit brand keywords
            Resume(
                filename="04_paraphrased_backend.txt",
                candidate_name="04 Paraphrased Backend",
                skills=[],  # Zero keyword credit
                experience_years=2.5,
                raw_text="""Experience:
Architected asynchronous HTTP web endpoints and microservice architectures.
Designed relational SQL database models, migration scripts, and index optimizations.
Maintained containerized deployment pipelines on cloud infrastructure."""
            ),
            # 5. Full-stack match (React + Python backend)
            Resume(
                filename="05_fullstack.txt",
                candidate_name="05 Full Stack",
                skills=["python", "postgresql", "react"],
                experience_years=2.0,
                raw_text="""Experience:
Developed Python web services and integrated PostgreSQL databases.
Built frontend user interfaces in React."""
            ),
            # 6. Frontend-heavy candidate
            Resume(
                filename="06_frontend_heavy.txt",
                candidate_name="06 Frontend Heavy",
                skills=["react", "javascript", "tailwind"],
                experience_years=2.5,
                raw_text="""Experience:
Created responsive web user interfaces in React with Tailwind CSS.
Integrated backend API endpoints."""
            ),
            # 7. QA / Automation candidate
            Resume(
                filename="07_qa_automation.txt",
                candidate_name="07 QA Automation",
                skills=["python"],
                experience_years=2.0,
                raw_text="""Experience:
Built automated testing suites in Python using pytest and selenium.
Validated REST API endpoints and database integrity."""
            ),
            # 8. DevOps candidate
            Resume(
                filename="08_devops.txt",
                candidate_name="08 DevOps",
                skills=["docker", "aws", "kubernetes"],
                experience_years=3.0,
                raw_text="""Experience:
Configured Docker containers and Kubernetes clusters on AWS cloud.
Maintained CI/CD pipelines and deployment infrastructure."""
            ),
            # 9. Data engineering candidate
            Resume(
                filename="09_data_engineer.txt",
                candidate_name="09 Data Engineer",
                skills=["python", "postgresql"],
                experience_years=2.0,
                raw_text="""Experience:
Built data ingestion ETL pipelines in Python.
Optimized PostgreSQL data warehouse queries."""
            ),
            # 10. Mobile developer
            Resume(
                filename="10_mobile_dev.txt",
                candidate_name="10 Mobile Dev",
                skills=["swift"],
                experience_years=2.0,
                raw_text="""Experience:
Developed native iOS mobile applications in Swift with SQLite local caching."""
            ),
            # 11. Java backend developer
            Resume(
                filename="11_java_backend.txt",
                candidate_name="11 Java Backend",
                skills=["java", "spring boot", "postgresql"],
                experience_years=3.0,
                raw_text="""Experience:
Architected enterprise microservices in Java and Spring Boot.
Designed PostgreSQL schemas and transaction processing."""
            ),
            # 12. Python data scientist
            Resume(
                filename="12_data_scientist.txt",
                candidate_name="12 Data Scientist",
                skills=["python"],
                experience_years=2.0,
                raw_text="""Experience:
Built predictive machine learning models in Python using scikit-learn and pandas."""
            ),
            # 13. Cloud engineer
            Resume(
                filename="13_cloud_engineer.txt",
                candidate_name="13 Cloud Engineer",
                skills=["aws", "docker"],
                experience_years=2.0,
                raw_text="""Experience:
Provisioned AWS cloud infrastructure using Terraform and deployed Docker containers."""
            ),
            # 14. Student with strong projects
            Resume(
                filename="14_student_projects.txt",
                candidate_name="14 Student Projects",
                skills=["python", "fastapi", "postgresql"],
                experience_years=0.0,
                projects=[
                    ProjectEntry(
                        name="FastAPI Service",
                        description="Developed asynchronous REST APIs in FastAPI with PostgreSQL database models."
                    )
                ],
                raw_text="""Projects:
Developed asynchronous REST APIs in FastAPI with PostgreSQL database models."""
            ),
            # 15. Student with basic skills
            Resume(
                filename="15_student_basic.txt",
                candidate_name="15 Student Basic",
                skills=["python"],
                experience_years=0.0,
                raw_text="""Education: Computer Science Student. Skills: Python."""
            ),
            # 16. Generic software candidate
            Resume(
                filename="16_generic_software.txt",
                candidate_name="16 Generic Software",
                skills=[],
                experience_years=2.0,
                raw_text="""Experience:
Spearheaded cross-functional technical initiatives and improved software quality across team sprints."""
            ),
            # 17. Marketing candidate
            Resume(
                filename="17_marketer.txt",
                candidate_name="17 Marketer",
                skills=[],
                experience_years=2.0,
                raw_text="""Experience:
Managed digital marketing campaigns, Google Ads, and social media audience growth."""
            ),
            # 18. Completely unrelated candidate (Pastry Chef)
            Resume(
                filename="18_pastry_chef.txt",
                candidate_name="18 Pastry Chef",
                skills=[],
                experience_years=4.0,
                raw_text="""Experience:
Prepared artisanal French pastries, croissants, and sourdough breads in high-volume bakery."""
            )
        ]

        assert len(candidates) == 18

        ranked_results = HybridRanker.rank_batch(jd, candidates)
        assert len(ranked_results) == 18

        # Extract ranked candidate names
        ranked_names = [r.resume.candidate_name for r in ranked_results]

        # 1. Candidate 01 (Excellent Backend) should be #1
        assert ranked_names[0] == "01 Excellent Backend"
        assert ranked_results[0].final_score > 0.65

        # 2. Unrelated candidates (Chef, Marketer) must be at the very bottom
        bottom_3 = ranked_names[-3:]
        assert "18 Pastry Chef" in bottom_3
        assert "17 Marketer" in bottom_3
        assert ranked_results[-1].final_score < 0.15

        # 3. Candidate with exact required skills beats candidate with only vague general buzzwords
        idx_fullstack = ranked_names.index("05 Full Stack")
        idx_generic = ranked_names.index("16 Generic Software")
        assert idx_fullstack < idx_generic

        # 4. Fresher with strong backend skills (02) ranks high despite 0 yrs experience penalty
        idx_fresher_strong = ranked_names.index("02 Fresher Strong Backend")
        assert idx_fresher_strong < 5  # Must remain in top tier (top 5)

        # 5. Missing required skills matters: Java dev (missing Python & FastAPI) ranks below Python Backend
        idx_java = ranked_names.index("11 Java Backend")
        idx_excellent = ranked_names.index("01 Excellent Backend")
        assert idx_excellent < idx_java
