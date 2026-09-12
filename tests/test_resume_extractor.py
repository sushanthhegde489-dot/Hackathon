import pytest
from extraction.resume_extractor import ResumeExtractor
from app.models import Resume

class TestResumeExtractor:
    def test_resume_parsing_and_sections(self):
        resume_text = """
        John Doe
        john.doe@example.com
        +1 555-123-4567

        Professional Summary:
        Aspiring full-stack engineer with hands-on internship experience.

        Technical Skills:
        Languages: JavaScript, TypeScript, Python
        Frameworks: React.js, Express, Node.js
        Databases: MongoDB, PostgreSQL
        Tools: Git, Docker

        Work Experience:
        Software Engineering Intern - Acme Corp (2023 - 2024)
        - Developed REST APIs with Node.js and Express.
        - Built frontend components using React.

        Education:
        B.Tech in Computer Science, 2024
        """
        resume = ResumeExtractor.parse_resume("john_doe.pdf", resume_text)

        assert isinstance(resume, Resume)
        assert resume.candidate_name == "John Doe"
        assert resume.email == "john.doe@example.com"
        assert "555-123-4567" in resume.phone
        assert "skills" in resume.sections
        assert "experience" in resume.sections
        assert "education" in resume.sections

        # Check extracted skills
        skills_set = set(resume.skills)
        assert "javascript" in skills_set
        assert "typescript" in skills_set
        assert "python" in skills_set
        assert "react" in skills_set
        assert "express" in skills_set
        assert "nodejs" in skills_set
        assert "mongodb" in skills_set
        assert "docker" in skills_set

    def test_no_hallucination_of_structured_entries(self):
        # We must not invent structured experience_entries, projects, etc.
        # if detailed parsing cannot be performed reliably
        resume_text = """
        Jane Smith
        jane@example.com
        Skills: React, Node.js
        """
        resume = ResumeExtractor.parse_resume("jane_smith.pdf", resume_text)
        assert resume.experience_entries == []
        assert resume.projects == []
        assert resume.education == []
        assert resume.certifications == []

    def test_resume_to_dict_structure(self):
        resume_text = "Alice Bob\nalice@example.com\nSkills: Python, AWS"
        resume = ResumeExtractor.parse_resume("alice.pdf", resume_text)
        d = resume.to_dict()

        assert d["candidate_name"] == "Alice Bob"
        assert d["email"] == "alice@example.com"
        assert "skills" in d
        assert "experience_entries" in d
        assert "projects" in d
        assert "education" in d
        assert "sections" in d
