import pytest
from extraction.jd_extractor import JDExtractor
from app.models import JobDescription

class TestJDExtractor:
    def test_required_vs_preferred_classification_by_cue(self):
        jd_text = """
        Job Title: Full Stack Developer
        Overview:
        We build modern web applications using microservices.

        Requirements:
        Must have strong proficiency in React and Node.js.
        Experience with PostgreSQL and Docker is required.

        Preferred Qualifications:
        Familiarity with AWS is nice to have.
        Bonus points for experience with GraphQL and Kubernetes.

        About TechNova:
        We also utilize CI/CD workflows and Git for our development lifecycle.
        """
        required, preferred, contextual, evidences = JDExtractor.extract_and_classify_skills(jd_text)

        # React, Node.js, PostgreSQL, Docker must be classified as required
        assert "react" in required
        assert "nodejs" in required
        assert "postgresql" in required
        assert "docker" in required

        # AWS, GraphQL, Kubernetes must be classified as preferred
        assert "aws" in preferred
        assert "graphql" in preferred
        assert "kubernetes" in preferred

        # Microservices, CI/CD, Git appear in overview/about section without required cues -> contextual
        assert "microservices" in contextual or "ci/cd" in contextual or "git" in contextual

        # Evidences check
        assert evidences["react"].classification == "required"
        assert evidences["react"].confidence >= 0.85
        assert "react" in evidences["react"].source_context.lower()

        assert evidences["aws"].classification == "preferred"
        assert evidences["aws"].confidence >= 0.85

    def test_in_sentence_cue_overrides_ambiguous_section(self):
        jd_text = """
        General Description:
        - Candidate must have hands-on experience with Python.
        - Having exposure to Redis is a nice to have bonus.
        - We operate in an Agile team.
        """
        required, preferred, contextual, evidences = JDExtractor.extract_and_classify_skills(jd_text)

        assert "python" in required
        assert "redis" in preferred
        assert "agile" in contextual

    def test_preserve_uncertainty_without_cues(self):
        # A technology merely appearing somewhere in a JD without requirement cues must NOT be classified as required!
        jd_text = """
        Tech Stack Overview:
        Our architecture relies on TypeScript, MongoDB, and Next.js.
        """
        required, preferred, contextual, evidences = JDExtractor.extract_and_classify_skills(jd_text)

        assert "typescript" not in required
        assert "mongodb" not in required
        assert "nextjs" not in required

        # Should be preserved as contextual
        assert "typescript" in contextual
        assert "mongodb" in contextual
        assert "nextjs" in contextual

    def test_experience_extraction(self):
        text1 = "Minimum of 3+ years of experience in software development."
        assert JDExtractor.extract_required_experience(text1) == 3.0

        text2 = "Candidate should have at least 2 years of experience."
        assert JDExtractor.extract_required_experience(text2) == 2.0

        text3 = "0 to 1 years of experience required for intern role."
        assert JDExtractor.extract_required_experience(text3) == 0.0

        text4 = "Freshers welcome, no experience required."
        assert JDExtractor.extract_required_experience(text4) == 0.0

    def test_title_extraction(self):
        text = "Junior Full Stack Developer Intern\nTechNova Solutions\nBangalore, India"
        title = JDExtractor.extract_title(text)
        assert "Developer" in title or "Intern" in title

    def test_parse_jd_full_model(self):
        jd_text = """
        Junior Software Engineer
        Requirements:
        - Must have experience with Java and Spring Boot.
        Preferred:
        - Familiarity with Docker is a plus.
        """
        jd = JDExtractor.parse_jd("test_jd.pdf", jd_text)
        assert isinstance(jd, JobDescription)
        assert jd.filename == "test_jd.pdf"
        assert "java" in jd.required_skills
        assert "spring boot" in jd.required_skills
        assert "docker" in jd.preferred_skills
        assert set(jd.all_skills()) == {"java", "spring boot", "docker"}

        jd_dict = jd.to_dict()
        assert "required_skills" in jd_dict
        assert "preferred_skills" in jd_dict
        assert "contextual_skills" in jd_dict
        assert "skill_evidences" in jd_dict
