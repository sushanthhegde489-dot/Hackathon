import pytest
from ingestion.text_cleaner import TextCleaner

class TestTextCleaner:
    def test_technical_tokens_preservation(self):
        sample = (
            "We build applications using C++, C#, .NET Core, Node.js, Next.js, "
            "CI/CD pipelines, REST API design, and React.js."
        )
        tokens = TextCleaner.extract_words(sample)
        token_set = set(tokens)

        assert "c++" in token_set
        assert "c#" in token_set
        assert ".net" in token_set
        assert "node.js" in token_set
        assert "next.js" in token_set
        assert "ci/cd" in token_set
        assert "react.js" in token_set
        assert "rest" in token_set
        assert "api" in token_set

    def test_technical_tokens_with_brackets_and_punctuation(self):
        sample = "Skills needed: [C++], (C#), {.NET}, Node.js/Express, and CI/CD/Docker."
        tokens = TextCleaner.extract_words(sample)
        token_set = set(tokens)

        assert "c++" in token_set
        assert "c#" in token_set
        assert ".net" in token_set
        assert "node.js" in token_set
        assert "express" in token_set
        assert "ci/cd" in token_set
        assert "docker" in token_set

    def test_clean_text_normalizes_whitespace_and_quotes(self):
        text = "Senior   Developer\u00a0Role:\n\n‘Building’ “fast” CI/CD—pipelines."
        cleaned = TextCleaner.clean_text(text)
        assert cleaned == "senior developer role: 'building' \"fast\" ci/cd-pipelines."

    def test_empty_and_none_input(self):
        assert TextCleaner.clean_text("") == ""
        assert TextCleaner.clean_text(None) == ""
        assert TextCleaner.extract_words("") == []
        assert TextCleaner.extract_words(None) == []

    def test_non_string_input(self):
        assert TextCleaner.clean_text(12345) == "12345"
        assert TextCleaner.extract_words(12345) == ["12345"]
