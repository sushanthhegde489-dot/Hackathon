import pytest
from app.config import RankingConfig
from app.models import JobDescription, Resume, CandidateResult
from app.matching.keyword_matcher import KeywordMatcher
from extraction.jd_extractor import JDExtractor
from extraction.resume_extractor import ResumeExtractor

class TestKeywordMatcherBasic:
    @pytest.fixture
    def sample_jd(self):
        return JobDescription(
            filename="backend_jd.pdf",
            raw_text="Backend Developer role",
            title="Backend Developer",
            required_skills=["python", "fastapi", "postgresql"],
            preferred_skills=["docker", "aws"]
        )

    def test_all_required_skills_matched(self, sample_jd):
        resume = Resume(
            filename="candidate_full_req.pdf",
            raw_text="Experienced in Python, FastAPI, and PostgreSQL.",
            candidate_name="Alice",
            skills=["python", "fastapi", "postgresql"]
        )
        result = KeywordMatcher.match(sample_jd, resume)

        assert result.keyword_breakdown.required_skill_score == 1.0
        assert set(result.keyword_breakdown.matched_required_skills) == {"python", "fastapi", "postgresql"}
        assert result.keyword_breakdown.missing_required_skills == []
        # Preferred skills not matched -> score is 0.70 (1.0 * 0.70 + 0.0 * 0.30)
        assert result.keyword_score == 0.70

    def test_some_required_skills_matched(self, sample_jd):
        resume = Resume(
            filename="candidate_partial_req.pdf",
            raw_text="Experienced in Python and PostgreSQL.",
            candidate_name="Bob",
            skills=["python", "postgresql"]
        )
        result = KeywordMatcher.match(sample_jd, resume)

        # 2 out of 3 matched
        assert round(result.keyword_breakdown.required_skill_score, 4) == round(2 / 3, 4)
        assert set(result.keyword_breakdown.matched_required_skills) == {"python", "postgresql"}
        assert result.keyword_breakdown.missing_required_skills == ["fastapi"]
        # (2/3 * 0.70) = 0.4667
        assert round(result.keyword_score, 4) == round((2 / 3) * 0.70, 4)

    def test_no_required_skills_matched(self, sample_jd):
        resume = Resume(
            filename="candidate_no_req.pdf",
            raw_text="Experienced in Ruby and Rails.",
            candidate_name="Charlie",
            skills=["ruby", "rails"]
        )
        result = KeywordMatcher.match(sample_jd, resume)

        assert result.keyword_breakdown.required_skill_score == 0.0
        assert result.keyword_breakdown.matched_required_skills == []
        assert set(result.keyword_breakdown.missing_required_skills) == {"python", "fastapi", "postgresql"}
        assert result.keyword_score == 0.0

    def test_all_preferred_skills_matched(self, sample_jd):
        resume = Resume(
            filename="candidate_pref.pdf",
            raw_text="Cloud dev with Docker and AWS.",
            candidate_name="Diana",
            skills=["docker", "aws"]
        )
        result = KeywordMatcher.match(sample_jd, resume)

        assert result.keyword_breakdown.preferred_skill_score == 1.0
        assert set(result.keyword_breakdown.matched_preferred_skills) == {"docker", "aws"}
        assert result.keyword_breakdown.missing_preferred_skills == []
        assert result.keyword_breakdown.required_skill_score == 0.0
        # 0.0 * 0.70 + 1.0 * 0.30 = 0.30
        assert result.keyword_score == 0.30

    def test_partial_preferred_skills_matched(self, sample_jd):
        resume = Resume(
            filename="candidate_partial_pref.pdf",
            raw_text="Dev with Docker.",
            candidate_name="Evan",
            skills=["docker"]
        )
        result = KeywordMatcher.match(sample_jd, resume)

        # 1 of 2 preferred
        assert result.keyword_breakdown.preferred_skill_score == 0.50
        assert result.keyword_breakdown.matched_preferred_skills == ["docker"]
        assert result.keyword_breakdown.missing_preferred_skills == ["aws"]
        # 0.50 * 0.30 = 0.15
        assert result.keyword_score == 0.15

    def test_all_required_and_preferred_matched(self, sample_jd):
        resume = Resume(
            filename="candidate_perfect.pdf",
            raw_text="Expert in Python, FastAPI, PostgreSQL, Docker, and AWS.",
            candidate_name="Fiona",
            skills=["python", "fastapi", "postgresql", "docker", "aws"]
        )
        result = KeywordMatcher.match(sample_jd, resume)

        assert result.keyword_breakdown.required_skill_score == 1.0
        assert result.keyword_breakdown.preferred_skill_score == 1.0
        assert result.keyword_score == 1.00


class TestKeywordMatcherWeighting:
    def test_configurable_weights_affect_scores(self):
        jd = JobDescription(
            filename="jd.pdf",
            raw_text="Role",
            required_skills=["python"],
            preferred_skills=["docker"]
        )
        # Candidate matches only required
        resume_req = Resume(filename="r1.pdf", raw_text="", skills=["python"])
        # Candidate matches only preferred
        resume_pref = Resume(filename="r2.pdf", raw_text="", skills=["docker"])

        # Default weights: req 0.70, pref 0.30
        res_req_default = KeywordMatcher.match(jd, resume_req)
        res_pref_default = KeywordMatcher.match(jd, resume_pref)
        assert res_req_default.keyword_score == 0.70
        assert res_pref_default.keyword_score == 0.30

        # Custom weights: req 0.85, pref 0.15
        custom_cfg = RankingConfig(required_skill_weight=0.85, preferred_skill_weight=0.15)
        res_req_custom = KeywordMatcher.match(jd, resume_req, config=custom_cfg)
        res_pref_custom = KeywordMatcher.match(jd, resume_pref, config=custom_cfg)
        assert res_req_custom.keyword_score == 0.85
        assert res_pref_custom.keyword_score == 0.15


class TestKeywordMatcherFalsePositives:
    def test_java_vs_javascript(self):
        # JD requires Java
        jd = JobDescription(filename="jd.pdf", raw_text="", required_skills=["java"])
        # Candidate only has JavaScript
        resume = Resume(filename="r.pdf", raw_text="JavaScript frontend developer", skills=["javascript"])

        result = KeywordMatcher.match(jd, resume)
        assert "java" not in result.keyword_breakdown.matched_required_skills
        assert "java" in result.keyword_breakdown.missing_required_skills
        assert result.keyword_score == 0.0

    def test_c_vs_cpp(self):
        jd = JobDescription(filename="jd.pdf", raw_text="", required_skills=["c"])
        resume = Resume(filename="r.pdf", raw_text="C++ systems developer", skills=["c++"])

        result = KeywordMatcher.match(jd, resume)
        assert "c" not in result.keyword_breakdown.matched_required_skills
        assert "c" in result.keyword_breakdown.missing_required_skills
        assert result.keyword_score == 0.0

    def test_cpp_vs_csharp(self):
        jd = JobDescription(filename="jd.pdf", raw_text="", required_skills=["c++"])
        resume = Resume(filename="r.pdf", raw_text="C# developer", skills=["c#"])

        result = KeywordMatcher.match(jd, resume)
        assert "c++" not in result.keyword_breakdown.matched_required_skills
        assert result.keyword_score == 0.0

    def test_react_vs_react_native(self):
        jd = JobDescription(filename="jd.pdf", raw_text="", required_skills=["react"])
        resume = Resume(filename="r.pdf", raw_text="React Native mobile developer", skills=["react native"])

        result = KeywordMatcher.match(jd, resume)
        assert "react" not in result.keyword_breakdown.matched_required_skills
        assert "react" in result.keyword_breakdown.missing_required_skills
        assert result.keyword_score == 0.0

    def test_node_vs_django(self):
        """Ensure unrelated frameworks do not falsely match."""
        jd = JobDescription(
            title="Backend Dev",
            required_skills=["nodejs"]
        )
        resume = Resume(
            filename="r.pdf",
            raw_text="Django API developer"
        )
        result = KeywordMatcher.match(jd, resume)
        assert "nodejs" not in result.keyword_breakdown.matched_required_skills
        assert result.keyword_score == 0.0

    def test_mongodb_vs_sql(self):
        jd = JobDescription(filename="jd.pdf", raw_text="", required_skills=["mongodb"])
        resume = Resume(filename="r.pdf", raw_text="SQL database developer", skills=["postgresql", "mysql"])

        result = KeywordMatcher.match(jd, resume)
        assert "mongodb" not in result.keyword_breakdown.matched_required_skills
        assert result.keyword_score == 0.0

    def test_aws_vs_docker(self):
        jd = JobDescription(filename="jd.pdf", raw_text="", required_skills=["aws"])
        resume = Resume(filename="r.pdf", raw_text="Docker containerization expert", skills=["docker"])

        result = KeywordMatcher.match(jd, resume)
        assert "aws" not in result.keyword_breakdown.matched_required_skills
        assert result.keyword_score == 0.0

    def test_python_vs_django(self):
        jd = JobDescription(filename="jd.pdf", raw_text="", required_skills=["python"])
        # If someone explicitly only has django listed without python
        resume = Resume(filename="r.pdf", raw_text="Django developer", skills=["django"])

        result = KeywordMatcher.match(jd, resume)
        assert "python" not in result.keyword_breakdown.matched_required_skills
        assert result.keyword_score == 0.0


class TestKeywordMatcherNormalization:
    def test_canonical_synonym_matching(self):
        jd = JobDescription(
            filename="jd.pdf",
            raw_text="Role",
            required_skills=["React.js", "Node.js", "RESTful API", "MongoDB"]
        )
        # Candidate uses equivalent synonyms
        resume = Resume(
            filename="r.pdf",
            raw_text="Skills: reactjs, node, rest api, mongo",
            skills=["reactjs", "node", "rest api", "mongo"]
        )
        result = KeywordMatcher.match(jd, resume)

        assert result.keyword_breakdown.required_skill_score == 1.0
        assert set(result.keyword_breakdown.matched_required_skills) == {"react", "nodejs", "rest api", "mongodb"}
        assert result.keyword_breakdown.missing_required_skills == []


class TestKeywordMatcherEmptyCases:
    def test_jd_with_no_required_skills(self):
        jd = JobDescription(
            filename="jd_no_req.pdf",
            raw_text="Exploratory role",
            required_skills=[],
            preferred_skills=["docker"]
        )
        resume = Resume(filename="r.pdf", raw_text="", skills=["docker"])
        result = KeywordMatcher.match(jd, resume)

        assert result.keyword_breakdown.required_skill_score == 0.0
        assert result.keyword_breakdown.preferred_skill_score == 1.0
        assert result.keyword_score == 0.30

    def test_jd_with_no_preferred_skills(self):
        jd = JobDescription(
            filename="jd_no_pref.pdf",
            raw_text="Strict role",
            required_skills=["python"],
            preferred_skills=[]
        )
        resume = Resume(filename="r.pdf", raw_text="", skills=["python"])
        result = KeywordMatcher.match(jd, resume)

        assert result.keyword_breakdown.required_skill_score == 1.0
        assert result.keyword_breakdown.preferred_skill_score == 0.0
        assert result.keyword_score == 0.70

    def test_resume_with_no_skills(self):
        jd = JobDescription(
            filename="jd.pdf",
            raw_text="Role",
            required_skills=["python"],
            preferred_skills=["docker"]
        )
        resume = Resume(filename="empty.pdf", raw_text="", skills=[])
        result = KeywordMatcher.match(jd, resume)

        assert result.keyword_breakdown.required_skill_score == 0.0
        assert result.keyword_breakdown.preferred_skill_score == 0.0
        assert result.keyword_score == 0.0

    def test_empty_jd_and_empty_resume(self):
        jd = JobDescription(filename="empty.pdf", raw_text="")
        resume = Resume(filename="empty.pdf", raw_text="")
        result = KeywordMatcher.match(jd, resume)

        assert result.keyword_score == 0.0
        assert result.keyword_breakdown.matched_required_skills == []
        assert result.keyword_breakdown.missing_required_skills == []


class TestKeywordMatcherEvidence:
    def test_evidence_structure_and_provenance(self):
        jd = JobDescription(
            filename="jd.pdf",
            raw_text="Role",
            required_skills=["React.js", "Docker"]
        )
        resume = Resume(
            filename="candidate.pdf",
            raw_text="Built UI using React.",
            skills=["react"],
            sections={"experience": "Developed web applications with React on the frontend."}
        )
        result = KeywordMatcher.match(jd, resume)
        evidence = result.keyword_breakdown.evidence

        # Matched skill evidence
        assert "react" in evidence
        assert evidence["react"]["status"] == "matched"
        assert evidence["react"]["tier"] == "required"
        assert evidence["react"]["jd_skill"] == "React.js"
        assert evidence["react"]["candidate_skill"] == "react"
        assert evidence["react"]["matching_method"] == "exact_canonical"
        assert evidence["react"]["source_section"] == "experience"
        assert "React" in evidence["react"]["source_context"]

        # Missing skill evidence
        assert "docker" in evidence
        assert evidence["docker"]["status"] == "missing"
        assert evidence["docker"]["tier"] == "required"
        assert evidence["docker"]["candidate_skill"] is None
        assert evidence["docker"]["matching_method"] == "none"
        assert evidence["docker"]["source_context"] is None


class TestExtractionToMatchingPipeline:
    def test_pipeline_with_synthetic_fixtures(self):
        jd_text = """
        Job Title: Senior Backend Engineer
        Requirements:
        Must have strong proficiency in Python, FastAPI, and PostgreSQL.
        Preferred Qualifications:
        Experience with Docker and AWS is nice to have.
        """
        parsed_jd = JDExtractor.parse_jd("backend_jd.pdf", jd_text)

        # Resume A: Matches all required + 1 preferred
        resume_a_text = """
        Alice Candidate
        Technical Skills:
        Languages: Python
        Frameworks: FastAPI
        Databases: PostgreSQL
        Tools: Docker
        """
        resume_a = ResumeExtractor.parse_resume("resume_a.pdf", resume_a_text)

        # Resume B: Matches Python, missing FastAPI & PostgreSQL, has Django & MySQL
        resume_b_text = """
        Bob Candidate
        Technical Skills:
        Languages: Python
        Frameworks: Django
        Databases: MySQL
        """
        resume_b = ResumeExtractor.parse_resume("resume_b.pdf", resume_b_text)

        # Resume C: Irrelevant tech stack (JavaScript, React, Node.js)
        resume_c_text = """
        Charlie Candidate
        Technical Skills:
        Languages: JavaScript
        Frameworks: React.js, Node.js
        """
        resume_c = ResumeExtractor.parse_resume("resume_c.pdf", resume_c_text)

        # Run batch matching
        ranked_results = KeywordMatcher.match_batch(parsed_jd, [resume_a, resume_b, resume_c])

        # Verify ranking order: A > B > C
        assert ranked_results[0].resume.candidate_name == "Alice Candidate"
        assert ranked_results[1].resume.candidate_name == "Bob Candidate"
        assert ranked_results[2].resume.candidate_name == "Charlie Candidate"

        # Check exact scores
        # Resume A: 3/3 req (1.0 * 0.70 = 0.70) + 1/2 pref (0.5 * 0.30 = 0.15) = 0.85
        assert ranked_results[0].keyword_score == 0.85
        assert set(ranked_results[0].keyword_breakdown.matched_required_skills) == {"python", "fastapi", "postgresql"}
        assert ranked_results[0].keyword_breakdown.matched_preferred_skills == ["docker"]

        # Resume B: 2/3 req (python, postgresql via mysql) (0.6667 * 0.70 = 0.4667) + 0/2 pref = 0.4667
        assert round(ranked_results[1].keyword_score, 4) == round((2 / 3) * 0.70, 4)
        assert set(ranked_results[1].keyword_breakdown.matched_required_skills) == {"python", "postgresql"}
        assert set(ranked_results[1].keyword_breakdown.missing_required_skills) == {"fastapi"}

        # Resume C: 0/3 req + 0/2 pref = 0.0
        assert ranked_results[2].keyword_score == 0.0
        assert ranked_results[2].keyword_breakdown.matched_required_skills == []
