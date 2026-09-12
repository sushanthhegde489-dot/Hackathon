import re
from typing import List, Tuple
from app.models import JobDescription
from ingestion.text_cleaner import TextCleaner
from extraction.skill_normalizer import SkillNormalizer

class JDExtractor:
    """Extracts structured information from a Job Description PDF's text."""

    # Common list of tech skills to search for
    TECH_SKILLS_VOCAB = [
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "ruby", "php", "swift", "kotlin", "rust",
        "react", "angular", "vue", "next.js", "svelte", "jquery", "bootstrap", "tailwind",
        "node.js", "express", "django", "flask", "fastapi", "spring boot", "laravel", "rails",
        "mongodb", "postgresql", "mysql", "redis", "sqlite", "oracle", "sql server", "dynamodb",
        "aws", "azure", "gcp", "docker", "kubernetes", "git", "ci/cd", "jenkins", "terraform",
        "rest api", "graphql", "grpc", "microservices", "agile", "scrum"
    ]

    @classmethod
    def extract_title(cls, raw_text: str) -> str:
        """Attempts to extract the job title from the first few non-empty lines of raw text."""
        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
        if not lines:
            return "Unknown Job Title"
        
        # Often the first line is the company name or title. Let's look at first 3 lines
        for line in lines[:3]:
            # If line is short and has keywords like 'developer', 'engineer', 'intern', 'manager', 'lead'
            lower_line = line.lower()
            if any(word in lower_line for word in ["developer", "engineer", "intern", "analyst", "designer", "architect", "programmer"]):
                # Don't return long descriptive paragraphs
                if len(line) < 60:
                    return line
        return lines[0][:50]  # Fallback to first line truncated

    @classmethod
    def extract_required_experience(cls, raw_text: str) -> float:
        """
        Extracts required experience in years using regex.
        Looks for patterns like '3+ years', 'at least 2 years', '5 years of experience'.
        """
        text = raw_text.lower()
        
        # Regex patterns to find mentions of years of experience
        patterns = [
            r"(\d+(?:\.\d+)?)\s*(?:\+|-)?\s*year[s]?\s*(?:of\s*)?experience",
            r"experience\s*(?:of\s*)?(?:at\s*least\s*)?(\d+(?:\.\d+)?)\s*year[s]?",
            r"minimum\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*year[s]?"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                try:
                    # Return the first matching number as float
                    return float(matches[0])
                except ValueError:
                    continue
        return 0.0

    @classmethod
    def extract_skills(cls, raw_text: str) -> List[str]:
        """
        Scans the JD text against our tech skills vocabulary and extracts matching terms.
        Applies normalizations to ensure synonyms match correctly.
        """
        # Tokenize using the smart extractor that preserves ++, #, .net, node.js
        tokens = TextCleaner.extract_words(raw_text)
        token_set = set(tokens)
        
        matched_skills = []
        for skill in cls.TECH_SKILLS_VOCAB:
            skill_cleaned = skill.lower()
            
            # Simple direct match if the skill is a multi-word skill or has special chars
            if " " in skill_cleaned:
                # Use regex search for multi-word phrases
                pattern = r"\b" + re.escape(skill_cleaned) + r"\b"
                if re.search(pattern, raw_text.lower()):
                    matched_skills.append(skill)
            else:
                # Single word match in tokens to prevent substring false-positives
                # e.g., 'go' shouldn't match 'google' or 'ongoing'
                if skill_cleaned in token_set:
                    matched_skills.append(skill)
                    
        return SkillNormalizer.normalize_list(matched_skills)

    @classmethod
    def parse_jd(cls, filename: str, raw_text: str) -> JobDescription:
        """Parses raw text and returns a fully populated JobDescription model."""
        cleaned_text = TextCleaner.clean_text(raw_text)
        title = cls.extract_title(raw_text)
        skills = cls.extract_skills(raw_text)
        exp_required = cls.extract_required_experience(raw_text)
        
        return JobDescription(
            filename=filename,
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            title=title,
            required_skills=skills,
            experience_years_required=exp_required
        )
