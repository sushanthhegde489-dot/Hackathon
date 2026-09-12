import time
import pytest
import numpy as np
from app.config import RankingConfig
from app.models import JobDescription, Resume, ExperienceEntry, ProjectEntry, CandidateResult
from app.matching.semantic_matcher import SemanticMatcher
from app.matching.keyword_matcher import KeywordMatcher


@pytest.fixture(scope="module")
def shared_model():
    """Ensure embedding model is pre-loaded for tests."""
    return SemanticMatcher.get_model()


class TestSemanticMatcherBasicBehavior:
    """Verifies fundamental semantic similarity properties."""

    def test_relevant_vs_irrelevant_resume(self, shared_model):
        jd = JobDescription(
            filename="backend_jd.txt",
            raw_text="Backend Python Engineer\nRequired:\nDevelop scalable backend APIs and web services using Python.\nManage relational databases and write automated unit tests.",
            sections={
                "required": "Develop scalable backend APIs and web services using Python.\nManage relational databases and write automated unit tests."
            }
        )

        relevant_resume = Resume(
            filename="alice.txt",
            raw_text="Software Engineer\nExperience:\nBuilt Python microservices and HTTP APIs.\nDesigned PostgreSQL schemas and wrote pytest suites.",
            sections={
                "experience": "Built Python microservices and HTTP APIs.\nDesigned PostgreSQL schemas and wrote pytest suites."
            }
        )

        irrelevant_resume = Resume(
            filename="bob.txt",
            raw_text="Graphic Designer\nExperience:\nCreated brochures, logos, and digital illustrations using Adobe Photoshop.\nManaged corporate social media accounts and content calendar.",
            sections={
                "experience": "Created brochures, logos, and digital illustrations using Adobe Photoshop.\nManaged corporate social media accounts and content calendar."
            }
        )

        res_rel = SemanticMatcher.match(jd, relevant_resume)
        res_irrel = SemanticMatcher.match(jd, irrelevant_resume)

        assert res_rel.semantic_score > 0.40
        assert res_irrel.semantic_score < 0.15
        assert res_rel.semantic_score > res_irrel.semantic_score + 0.30

    def test_paraphrased_experience_without_exact_keywords(self, shared_model):
        """Verifies semantic matching recognizes equivalent concepts despite zero exact keywords."""
        jd = JobDescription(
            filename="api_jd.txt",
            raw_text="Required:\nDevelop REST APIs for web applications.",
            sections={"required": "Develop REST APIs for web applications."}
        )

        # Notice: Uses 'HTTP services' and 'backend endpoints' instead of 'REST APIs'
        paraphrased_resume = Resume(
            filename="charlie.txt",
            raw_text="Experience:\nBuilt HTTP services and backend endpoints for production web systems.",
            sections={"experience": "Built HTTP services and backend endpoints for production web systems."}
        )

        res = SemanticMatcher.match(jd, paraphrased_resume)
        assert res.semantic_score > 0.35

        # Check evidence captures the paraphrase with preserved source text
        assert len(res.semantic_breakdown.strongest_matches) > 0
        top_match = res.semantic_breakdown.strongest_matches[0]
        assert "Develop REST APIs" in top_match["jd_chunk"]
        assert "Built HTTP services" in top_match["resume_chunk"]
        assert top_match["similarity"] > 0.30

    def test_unrelated_experience_scores_substantially_lower(self, shared_model):
        jd = JobDescription(
            filename="data_jd.txt",
            raw_text="Required:\nBuild machine learning models and data pipelines in Python.",
            sections={"required": "Build machine learning models and data pipelines in Python."}
        )

        unrelated_resume = Resume(
            filename="dave.txt",
            raw_text="Experience:\nChef de Partie preparing Mediterranean pastries and artisan breads in high-volume bakery.",
            sections={"experience": "Chef de Partie preparing Mediterranean pastries and artisan breads in high-volume bakery."}
        )

        res = SemanticMatcher.match(jd, unrelated_resume)
        assert res.semantic_score < 0.10


class TestSemanticMatcherSectionAwareness:
    """Verifies that section structure influences semantic scoring appropriately."""

    def test_experience_and_projects_contribute(self, shared_model):
        jd = JobDescription(
            filename="jd_req.txt",
            raw_text="Required:\nContainerize applications and maintain deployment pipelines.",
            sections={"required": "Containerize applications and maintain deployment pipelines."}
        )

        resume_with_project = Resume(
            filename="proj_res.txt",
            raw_text="Projects:\nDockerized web microservices and set up automated CI/CD deployment pipelines using GitHub Actions.",
            projects=[
                ProjectEntry(
                    name="Cloud Deployer",
                    description="Dockerized web microservices and set up automated CI/CD deployment pipelines using GitHub Actions."
                )
            ]
        )

        res = SemanticMatcher.match(jd, resume_with_project)
        assert res.semantic_score > 0.35
        top_match = res.semantic_breakdown.strongest_matches[0]
        assert top_match["resume_section"] == "projects"

    def test_irrelevant_sections_do_not_dominate(self, shared_model):
        """A candidate with extensive irrelevant hobbies still gets scored on their relevant experience."""
        jd = JobDescription(
            filename="jd.txt",
            raw_text="Required:\nDevelop backend services using Python.",
            sections={"required": "Develop backend services using Python."}
        )

        resume = Resume(
            filename="candidate.txt",
            raw_text="Experience:\nDeveloped backend APIs and data services in Python.\nOther:\nAvid runner, mountain biker, scuba diver, landscape painter, amateur chess player.",
            sections={
                "experience": "Developed backend APIs and data services in Python.",
                "other": "Avid runner, mountain biker, scuba diver, landscape painter, amateur chess player."
            }
        )

        res = SemanticMatcher.match(jd, resume)
        assert res.semantic_score > 0.40
        top_match = res.semantic_breakdown.strongest_matches[0]
        assert top_match["resume_section"] == "experience"

    def test_missing_sections_do_not_crash(self, shared_model):
        """Matcher gracefully handles resumes with missing sections or unstructured text."""
        jd = JobDescription(
            filename="jd.txt",
            raw_text="Software Developer\nRequired:\nWrite clean Python code.",
            sections={"required": "Write clean Python code."}
        )

        # Completely unsectioned resume
        raw_resume = Resume(
            filename="unsectioned.txt",
            raw_text="Alice Smith - Experienced developer who writes clean Python code and tests.",
            sections={}
        )

        res = SemanticMatcher.match(jd, raw_resume)
        assert res.semantic_score > 0.30
        assert not np.isnan(res.semantic_score)


class TestKeywordSemanticIndependence:
    """Verifies that keyword scoring and semantic scoring are genuinely independent mechanisms."""

    def test_low_keyword_high_semantic_paraphrase(self, shared_model):
        """Candidate expresses equivalent skills using different vocabulary (Low Keyword, High Semantic)."""
        jd = JobDescription(
            filename="jd_kw.txt",
            raw_text="Required:\nDocker\nPostgreSQL\nFastAPI",
            required_skills=["docker", "postgresql", "fastapi"],
            sections={"required": "Docker\nPostgreSQL\nFastAPI"}
        )

        resume = Resume(
            filename="paraphrased.txt",
            raw_text="Experience:\nContainerized microservice workloads for cloud deployments.\nArchitected relational SQL databases for transaction processing.\nBuilt high-performance asynchronous REST endpoints in Python.",
            skills=[],  # Zero exact keyword matches
            sections={
                "experience": "Containerized microservice workloads for cloud deployments.\nArchitected relational SQL databases for transaction processing.\nBuilt high-performance asynchronous REST endpoints in Python."
            }
        )

        kw_res = KeywordMatcher.match(jd, resume)
        sem_res = SemanticMatcher.match(jd, resume)

        # Keyword score is zero (no exact keywords matched)
        assert kw_res.keyword_score == 0.0
        # Semantic score recognizes the conceptual equivalence
        assert sem_res.semantic_score > 0.20
        assert sem_res.semantic_score > kw_res.keyword_score + 0.20

    def test_high_keyword_weak_semantic_keyword_stuffing(self, shared_model):
        """Candidate stuffs keywords in skills list with zero contextual experience (High Keyword, Lower Semantic Depth)."""
        jd = JobDescription(
            filename="jd.txt",
            raw_text="Required:\nArchitect distributed backend streaming pipelines using Python, Kafka, and Spark.\nOptimize multi-node cluster performance and data throughput.",
            required_skills=["python"],
            sections={
                "required": "Architect distributed backend streaming pipelines using Python, Kafka, and Spark.\nOptimize multi-node cluster performance and data throughput."
            }
        )

        # Stuffed keyword list but completely trivial/unrelated experience
        stuffed_resume = Resume(
            filename="stuffed.txt",
            raw_text="Skills: Python\nExperience:\nWrote a hello-world script and edited text files in Python.",
            skills=["python"],
            sections={
                "skills": "Python",
                "experience": "Wrote a hello-world script and edited text files in Python."
            }
        )

        kw_res = KeywordMatcher.match(jd, stuffed_resume)
        sem_res = SemanticMatcher.match(jd, stuffed_resume)

        # Keyword matches 100% of required skills
        assert kw_res.keyword_score == 0.70  # 1.0 required * 0.70 default weight
        # Semantic score remains modest because complex streaming requirements find little contextual depth
        assert sem_res.semantic_score < 0.40


class TestSemanticFalsePositivePrevention:
    """Verifies that superficial document similarities do not trigger false positive semantic scores."""

    def test_unrelated_domains_low_semantic_score(self, shared_model):
        jd = JobDescription(
            filename="jd.txt",
            raw_text="Required:\nPython backend development with relational databases and unit testing.",
            sections={"required": "Python backend development with relational databases and unit testing."}
        )

        marketing_resume = Resume(
            filename="marketing.txt",
            raw_text="Professional Summary:\nAccomplished marketing specialist with 4 years in social media campaign management.\nExperience:\nDesigned promotional graphics, scheduled Instagram posts, and analyzed click-through metrics.",
            sections={
                "summary": "Accomplished marketing specialist with 4 years in social media campaign management.",
                "experience": "Designed promotional graphics, scheduled Instagram posts, and analyzed click-through metrics."
            }
        )

        res = SemanticMatcher.match(jd, marketing_resume)
        assert res.semantic_score < 0.10

    def test_professional_jargon_alone_does_not_yield_high_score(self, shared_model):
        """Generic resume jargon ('results-driven leader', 'spearheaded strategic synergies') does not fool semantic matching."""
        jd = JobDescription(
            filename="jd.txt",
            raw_text="Required:\nImplement cryptographic protocols and kernel-level network drivers in C++.",
            sections={"required": "Implement cryptographic protocols and kernel-level network drivers in C++."}
        )

        corporate_resume = Resume(
            filename="corporate.txt",
            raw_text="Experience:\nSpearheaded strategic leadership initiatives.\nChampioned high-impact synergy across cross-functional stakeholder ecosystems.\nDelivered optimal paradigm shifts in organizational excellence.",
            sections={
                "experience": "Spearheaded strategic leadership initiatives.\nChampioned high-impact synergy across cross-functional stakeholder ecosystems.\nDelivered optimal paradigm shifts in organizational excellence."
            }
        )

        res = SemanticMatcher.match(jd, corporate_resume)
        assert res.semantic_score < 0.10


class TestEdgeCasesAndMalformedInputs:
    """Verifies robustness against empty, malformed, and anomalous data."""

    def test_empty_jd(self, shared_model):
        jd = JobDescription(filename="empty.txt", raw_text="")
        resume = Resume(filename="cand.txt", raw_text="Experienced Python software engineer.")

        res = SemanticMatcher.match(jd, resume)
        assert res.semantic_score == 0.0
        assert res.semantic_breakdown.strongest_matches == []
        assert "error" in res.semantic_breakdown.similarity_evidence

    def test_empty_resume(self, shared_model):
        jd = JobDescription(filename="jd.txt", raw_text="Required:\nPython developer.")
        resume = Resume(filename="empty.txt", raw_text="")

        res = SemanticMatcher.match(jd, resume)
        assert res.semantic_score == 0.0
        assert res.semantic_breakdown.strongest_matches == []

    def test_whitespace_only(self, shared_model):
        jd = JobDescription(filename="jd.txt", raw_text="   \n\n\t  ")
        resume = Resume(filename="cand.txt", raw_text="   \t  ")

        res = SemanticMatcher.match(jd, resume)
        assert res.semantic_score == 0.0

    def test_very_short_text(self, shared_model):
        jd = JobDescription(filename="jd.txt", raw_text="Engineer", sections={"general": "Engineer"})
        resume = Resume(filename="cand.txt", raw_text="Dev", sections={"general": "Dev"})

        res = SemanticMatcher.match(jd, resume)
        assert 0.0 <= res.semantic_score <= 1.0
        assert not np.isnan(res.semantic_score)

    def test_duplicated_sections_deduplication(self, shared_model):
        jd = JobDescription(
            filename="dup.txt",
            raw_text="Python Engineer\nPython Engineer\nPython Engineer",
            sections={"general": "Python Engineer\nPython Engineer\nPython Engineer"}
        )
        chunks = SemanticMatcher.chunk_jd(jd)
        assert len(chunks) == 1

    def test_special_characters_and_formatting(self, shared_model):
        jd = JobDescription(
            filename="special.txt",
            raw_text="Required:\nC++ & C# microservices @ scale / multithreading (POSIX) -> 99.99% SLA.",
            sections={"required": "C++ & C# microservices @ scale / multithreading (POSIX) -> 99.99% SLA."}
        )
        resume = Resume(
            filename="cand.txt",
            raw_text="Experience:\nDesigned concurrent C++ services maintaining high availability and 99.99% uptime.",
            sections={"experience": "Designed concurrent C++ services maintaining high availability and 99.99% uptime."}
        )

        res = SemanticMatcher.match(jd, resume)
        assert 0.0 <= res.semantic_score <= 1.0
        assert res.semantic_score > 0.35


class TestSemanticEvidenceIntegrity:
    """Verifies that semantic evidence matches source text without hallucination."""

    def test_evidence_structure_and_provenance(self, shared_model):
        jd = JobDescription(
            filename="jd.txt",
            raw_text="Required:\nDesign PostgreSQL database schemas and write optimized queries.",
            sections={"required": "Design PostgreSQL database schemas and write optimized queries."}
        )
        resume = Resume(
            filename="cand.txt",
            raw_text="Experience:\nArchitected relational database schemas and indexed SQL queries for fast performance.",
            sections={"experience": "Architected relational database schemas and indexed SQL queries for fast performance."}
        )

        res = SemanticMatcher.match(jd, resume)
        evidence = res.semantic_breakdown

        assert len(evidence.strongest_matches) > 0
        top = evidence.strongest_matches[0]

        # Verify exact required fields
        assert "jd_chunk" in top
        assert "jd_section" in top
        assert "resume_chunk" in top
        assert "resume_section" in top
        assert "similarity" in top
        assert "raw_similarity" in top

        # Verify source text fidelity preserving original casing
        assert top["jd_chunk"] == "Design PostgreSQL database schemas and write optimized queries."
        assert top["resume_chunk"] == "Architected relational database schemas and indexed SQL queries for fast performance."
        assert top["jd_section"] == "required"
        assert top["resume_section"] == "experience"
        assert 0.0 <= top["similarity"] <= 1.0
        assert 0.0 <= top["raw_similarity"] <= 1.0

        # Verify section breakdown
        assert "section_scores" in evidence.similarity_evidence
        assert "required" in evidence.similarity_evidence["section_scores"]


class TestRealisticSyntheticFixtures:
    """Tests realistic synthetic fixtures specified in the problem statement."""

    def test_synthetic_candidates_relative_ordering(self, shared_model):
        # Realistic Synthetic JD
        jd = JobDescription(
            filename="intern_jd.txt",
            title="Software Engineering Intern",
            raw_text="""Software Engineering Intern

Required:
Develop backend services and APIs using Python.
Work with relational databases.
Write tests and maintain production-quality code.

Preferred:
Docker and cloud deployment experience.

Responsibilities:
Collaborate with engineers to build scalable web applications.""",
            sections={
                "required": "Develop backend services and APIs using Python.\nWork with relational databases.\nWrite tests and maintain production-quality code.",
                "preferred": "Docker and cloud deployment experience.",
                "contextual": "Collaborate with engineers to build scalable web applications."
            }
        )

        # Resume A: Backend engineering intern
        resume_a = Resume(
            filename="resume_a.txt",
            candidate_name="Candidate A (Backend)",
            raw_text="""Backend engineering intern.
Built Python HTTP services and REST endpoints.
Designed PostgreSQL data models.
Created automated tests for backend services.
Worked with Docker deployments.""",
            sections={
                "summary": "Backend engineering intern.",
                "experience": "Built Python HTTP services and REST endpoints.\nDesigned PostgreSQL data models.\nCreated automated tests for backend services.\nWorked with Docker deployments."
            }
        )

        # Resume B: Frontend developer
        resume_b = Resume(
            filename="resume_b.txt",
            candidate_name="Candidate B (Frontend)",
            raw_text="""Frontend developer.
Built React interfaces and responsive web pages.
Worked with JavaScript and CSS.
Created UI components and design systems.""",
            sections={
                "summary": "Frontend developer.",
                "experience": "Built React interfaces and responsive web pages.\nWorked with JavaScript and CSS.\nCreated UI components and design systems."
            }
        )

        # Resume C: Marketing intern
        resume_c = Resume(
            filename="resume_c.txt",
            candidate_name="Candidate C (Marketing)",
            raw_text="""Marketing intern.
Created social media campaigns.
Designed promotional graphics.
Analyzed audience engagement.""",
            sections={
                "summary": "Marketing intern.",
                "experience": "Created social media campaigns.\nDesigned promotional graphics.\nAnalyzed audience engagement."
            }
        )

        res_a = SemanticMatcher.match(jd, resume_a)
        res_b = SemanticMatcher.match(jd, resume_b)
        res_c = SemanticMatcher.match(jd, resume_c)

        # Assert sensible ordering: Backend > Frontend > Marketing
        assert res_a.semantic_score > res_b.semantic_score
        assert res_b.semantic_score > res_c.semantic_score

        # Candidate A should have a strong score
        assert res_a.semantic_score > 0.35
        # Candidate C should have a negligible score
        assert res_c.semantic_score < 0.15

        # Verify batch matching produces identical relative ordering
        batch_results = SemanticMatcher.match_batch(jd, [resume_c, resume_a, resume_b])
        assert [r.resume.candidate_name for r in batch_results] == [
            "Candidate A (Backend)",
            "Candidate B (Frontend)",
            "Candidate C (Marketing)"
        ]


class TestBatchProcessingAndDeterminism:
    """Verifies batch execution consistency and determinism."""

    def test_batch_matches_single_match(self, shared_model):
        jd = JobDescription(
            filename="jd.txt",
            raw_text="Required:\nPython microservices development and containerization.",
            sections={"required": "Python microservices development and containerization."}
        )
        resumes = [
            Resume(filename="r1.txt", candidate_name="Cand1", raw_text="Experience:\nPython REST API microservices."),
            Resume(filename="r2.txt", candidate_name="Cand2", raw_text="Experience:\nDocker and Kubernetes container management.")
        ]

        single_res_0 = SemanticMatcher.match(jd, resumes[0])
        single_res_1 = SemanticMatcher.match(jd, resumes[1])

        batch_results = SemanticMatcher.match_batch(jd, resumes)

        batch_dict = {r.resume.filename: r.semantic_score for r in batch_results}
        assert batch_dict["r1.txt"] == single_res_0.semantic_score
        assert batch_dict["r2.txt"] == single_res_1.semantic_score

    def test_candidate_independence(self, shared_model):
        """Evaluating Candidate A alongside Candidate B vs alone yields the exact same score."""
        jd = JobDescription(
            filename="jd.txt",
            raw_text="Required:\nPython microservices.",
            sections={"required": "Python microservices."}
        )
        cand_a = Resume(filename="a.txt", candidate_name="Alice", raw_text="Python API development.")
        cand_b = Resume(filename="b.txt", candidate_name="Bob", raw_text="Marketing and graphics.")

        score_a_alone = SemanticMatcher.match(jd, cand_a).semantic_score

        batch = SemanticMatcher.match_batch(jd, [cand_a, cand_b])
        score_a_in_batch = next(r.semantic_score for r in batch if r.resume.filename == "a.txt")

        assert score_a_alone == score_a_in_batch


class TestPerformanceSmokeTest18Resumes:
    """
    Performance benchmark: 1 JD against 18 synthetic candidate resumes.
    Simulates the realistic hackathon workload.
    """

    def test_18_resumes_batch_smoke_test(self, shared_model):
        jd = JobDescription(
            filename="swe_intern_jd.txt",
            title="Software Engineering Intern",
            raw_text="""Software Engineering Intern
Required:
Develop backend microservices and APIs using Python.
Design and query relational databases with PostgreSQL.
Implement unit tests and CI/CD pipelines.
Preferred:
Docker and containerization experience.
AWS or cloud infrastructure exposure.
Responsibilities:
Collaborate with agile engineering teams to deliver robust software.""",
            sections={
                "required": "Develop backend microservices and APIs using Python.\nDesign and query relational databases with PostgreSQL.\nImplement unit tests and CI/CD pipelines.",
                "preferred": "Docker and containerization experience.\nAWS or cloud infrastructure exposure.",
                "contextual": "Collaborate with agile engineering teams to deliver robust software."
            }
        )

        # 18 diverse resumes with realistic multi-bullet descriptions representing varying relevance tiers
        candidates_data = [
            ("Backend Engineer", [
                "Built Python FastAPI microservices and scalable REST endpoints.",
                "Designed PostgreSQL relational schemas and query optimizations.",
                "Implemented automated unit test suites with pytest and CI/CD.",
                "Deployed containerized services using Docker on AWS cloud."
            ]),
            ("Python Developer", [
                "Developed Django web applications and backend APIs in Python.",
                "Integrated PostgreSQL databases and managed migrations.",
                "Wrote automated tests and maintained clean code.",
                "Configured Docker containers for development environments."
            ]),
            ("Full Stack Developer", [
                "Created React frontends and Python backend services.",
                "Designed relational database tables and RESTful endpoints.",
                "Wrote unit tests and deployed applications to cloud."
            ]),
            ("DevOps Intern", [
                "Configured Docker containers and Kubernetes clusters.",
                "Maintained GitHub Actions CI/CD pipelines and deployment scripts.",
                "Managed AWS cloud infrastructure and monitoring dashboards."
            ]),
            ("Backend Junior", [
                "Implemented Python backend endpoints for web services.",
                "Worked with relational database queries and bug fixes.",
                "Assisted with unit test development and agile team sprints."
            ]),
            ("Data Engineer Intern", [
                "Built data ingestion pipelines using Python and SQL.",
                "Optimized relational PostgreSQL database performance.",
                "Automated data workflows with dockerized tasks."
            ]),
            ("Cloud Engineer", [
                "Automated AWS cloud provisioning using Terraform.",
                "Deployed containerized services and managed Docker registries.",
                "Wrote automation scripts in Python and bash."
            ]),
            ("QA Automation Engineer", [
                "Created automated test frameworks for REST APIs.",
                "Wrote pytest test cases and validated database states.",
                "Integrated automated tests into CI/CD pipelines."
            ]),
            ("Systems Engineer", [
                "Developed Linux system utilities and network services.",
                "Wrote multi-threaded scripts in Python and C++.",
                "Maintained continuous deployment infrastructure."
            ]),
            ("Frontend Developer 1", [
                "Built responsive single-page web applications with React.",
                "Styled modern UI components using Tailwind CSS and HTML.",
                "Consumed REST API endpoints from backend services."
            ]),
            ("Frontend Developer 2", [
                "Created interactive web interfaces in Vue.js and JavaScript.",
                "Implemented design systems and client-side routing.",
                "Collaborated with product designers on user experience."
            ]),
            ("Mobile Developer 1", [
                "Developed cross-platform mobile apps using Flutter.",
                "Integrated RESTful backend APIs with mobile interfaces.",
                "Published updates to Google Play and Apple App Store."
            ]),
            ("Mobile Developer 2", [
                "Built native iOS applications in Swift.",
                "Managed local SQLite storage and offline sync.",
                "Designed responsive mobile user experiences."
            ]),
            ("Data Analyst", [
                "Created business intelligence dashboards in Tableau.",
                "Wrote complex SQL queries to extract analytical reports.",
                "Presented data insights to executive stakeholders."
            ]),
            ("UI/UX Designer", [
                "Created wireframes, user journeys, and prototypes in Figma.",
                "Conducted usability testing and user research sessions.",
                "Developed design guidelines and accessibility standards."
            ]),
            ("Product Manager", [
                "Managed product backlog and defined technical specifications.",
                "Facilitated agile sprint ceremonies, standups, and retrospectives.",
                "Coordinated feature delivery across cross-functional teams."
            ]),
            ("Technical Recruiter", [
                "Sourced and screened candidates for software engineering roles.",
                "Conducted initial phone screens and managed hiring pipeline.",
                "Partnered with engineering managers on hiring criteria."
            ]),
            ("Digital Marketer", [
                "Planned and executed digital advertising campaigns on Google Ads.",
                "Managed corporate social media accounts and email newsletters.",
                "Analyzed conversion funnels and web traffic in Google Analytics."
            ])
        ]

        resumes = [
            Resume(
                filename=f"candidate_{i+1:02d}.txt",
                candidate_name=f"Candidate {i+1:02d} ({role})",
                raw_text=f"Summary:\n{role}\nExperience:\n" + "\n".join(bullets),
                sections={
                    "summary": role,
                    "experience": "\n".join(bullets)
                }
            )
            for i, (role, bullets) in enumerate(candidates_data)
        ]

        assert len(resumes) == 18

        # Measure batch processing time
        start_time = time.perf_counter()
        results = SemanticMatcher.match_batch(jd, resumes)
        duration = time.perf_counter() - start_time

        # Verify all 18 results exist and are bounded
        assert len(results) == 18
        for r in results:
            assert 0.0 <= r.semantic_score <= 1.0
            assert len(r.semantic_breakdown.strongest_matches) > 0
            assert "section_scores" in r.semantic_breakdown.similarity_evidence

        # Verify top candidate is the strong Backend profile
        top_cand = results[0]
        assert "Backend" in top_cand.resume.candidate_name
        assert top_cand.semantic_score > 0.40

        # Verify bottom candidate is completely unrelated (Marketer or Recruiter)
        bottom_cand = results[-1]
        assert bottom_cand.semantic_score < 0.15

        print(f"\n[BENCHMARK] 18-resume batch semantic matching executed in {duration:.3f} seconds.")
        # Runtime must be within reasonable interactive limits (< 5 seconds on CPU)
        assert duration < 5.0
