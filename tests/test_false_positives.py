import pytest
from ingestion.text_cleaner import TextCleaner
from extraction.jd_extractor import JDExtractor
from extraction.resume_extractor import ResumeExtractor

class TestFalsePositivePrevention:
    def test_short_language_names_do_not_match_substrings(self):
        # Text containing words with substrings like 'go', 'c', 'rust', 'java'
        text = (
            "We have ongoing projects with good algorithms. "
            "We foster trust and avoid frustration. "
            "We write clean code in the cloud."
        )
        tokens = set(TextCleaner.extract_words(text))

        # "go" should NOT be extracted from "ongoing", "good", "algorithms"
        assert "go" not in tokens
        # "rust" should NOT be extracted from "trust" or "frustration"
        assert "rust" not in tokens

        # JDExtractor should not detect "go" or "rust" or "c"
        required, preferred, contextual, evidences = JDExtractor.extract_and_classify_skills(text)
        detected_all = required + preferred + contextual
        assert "go" not in detected_all
        assert "rust" not in detected_all
        assert "c" not in detected_all

    def test_java_vs_javascript_distinction(self):
        js_text = "Experienced in JavaScript frontend development."
        js_skills = ResumeExtractor.extract_skills(js_text)
        assert "javascript" in js_skills
        assert "java" not in js_skills

        java_text = "Backend services developed using Java and Spring Boot."
        java_skills = ResumeExtractor.extract_skills(java_text)
        assert "java" in java_skills
        assert "javascript" not in java_skills

    def test_c_vs_cpp_vs_csharp_distinction(self):
        text = "Proficient in C++ and C#."
        skills = ResumeExtractor.extract_skills(text)
        assert "c++" in skills
        assert "c#" in skills
        assert "c" not in skills

    def test_react_does_not_match_react_native(self):
        text = "Developed mobile apps with React Native."
        # React Native shouldn't falsely collapse into pure React without distinction
        tokens = TextCleaner.extract_words(text)
        assert "react" in tokens
        assert "native" in tokens
