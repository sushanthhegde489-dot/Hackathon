import pytest
from extraction.jd_extractor import JDExtractor
from extraction.resume_extractor import ResumeExtractor
from ingestion.text_cleaner import TextCleaner
from ingestion.pdf_parser import PDFParser

class TestEdgeCasesAndMalformedInput:
    def test_jd_empty_and_none_input(self):
        jd_empty = JDExtractor.parse_jd("empty.pdf", "")
        assert jd_empty.title == "Unknown Job Title"
        assert jd_empty.required_skills == []
        assert jd_empty.preferred_skills == []
        assert jd_empty.contextual_skills == []
        assert jd_empty.experience_years_required == 0.0

        jd_none = JDExtractor.parse_jd("none.pdf", None)
        assert jd_none.title == "Unknown Job Title"
        assert jd_none.required_skills == []
        assert jd_none.experience_years_required == 0.0

    def test_resume_empty_and_none_input(self):
        res_empty = ResumeExtractor.parse_resume("empty_res.pdf", "")
        assert res_empty.candidate_name == "empty_res"
        assert res_empty.email == ""
        assert res_empty.skills == []
        assert res_empty.experience_years == 0.0

        res_none = ResumeExtractor.parse_resume("none_res.pdf", None)
        assert res_none.candidate_name == "none_res"
        assert res_none.email == ""
        assert res_none.skills == []

    def test_malformed_unparseable_experience(self):
        text = "Experience: many many years of varied engineering leadership!"
        assert JDExtractor.extract_required_experience(text) == 0.0
        assert ResumeExtractor.extract_experience_years(text) == 0.0

    def test_special_characters_and_corrupted_tokens(self):
        malformed = "\x00\x01\x02\t\n###@@@%%%$$$*** &&& ??? ~~~ \n\n"
        cleaned = TextCleaner.clean_text(malformed)
        assert isinstance(cleaned, str)
        tokens = TextCleaner.extract_words(malformed)
        assert isinstance(tokens, list)

    def test_pdf_parser_nonexistent_and_directory(self):
        assert PDFParser.extract_text("non_existent_file_path_12345.pdf") == ""
        assert PDFParser.discover_pdfs("non_existent_directory_12345") == []
