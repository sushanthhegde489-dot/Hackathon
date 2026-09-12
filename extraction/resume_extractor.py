import re
from typing import List, Dict, Optional
from app.models import Resume, ExperienceEntry, ProjectEntry, EducationEntry
from ingestion.text_cleaner import TextCleaner
from extraction.skill_normalizer import SkillNormalizer

class ResumeExtractor:
    """
    Extracts structured and sectioned information from Candidate Resumes.
    Adheres strictly to the principle of not inventing information:
    extracts clear text sections, contact details, and verified skills,
    leaving complex structured entries empty rather than hallucinating.
    """

    EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    PHONE_PATTERN = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+?91[-.\s]?[6-9]\d{9}")

    SECTION_PATTERNS = {
        "skills": re.compile(r"^(?:technical\s+skills|skills\s*&?\s*technologies|skills|technologies|core\s+competencies)\b", re.IGNORECASE),
        "experience": re.compile(r"^(?:work\s+experience|professional\s+experience|experience|employment\s+history|internships)\b", re.IGNORECASE),
        "projects": re.compile(r"^(?:projects|academic\s+projects|personal\s+projects|key\s+projects)\b", re.IGNORECASE),
        "education": re.compile(r"^(?:education|academic\s+background|academics|qualifications)\b", re.IGNORECASE),
        "certifications": re.compile(r"^(?:certifications|certificates|licenses|achievements)\b", re.IGNORECASE),
        "summary": re.compile(r"^(?:professional\s+summary|summary|profile|about\s+me|objective)\b", re.IGNORECASE),
    }

    # Moved TECH_SKILLS_VOCAB to SkillNormalizer

    @classmethod
    def extract_name(cls, raw_text: Optional[str], fallback: str = "Unknown Candidate") -> str:
        """Extracts candidate name from the top non-empty lines."""
        if not raw_text or not raw_text.strip():
            return fallback

        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
        if not lines:
            return fallback

        for line in lines[:3]:
            # Filter out lines that look like headers, emails, or phone numbers
            if cls.EMAIL_PATTERN.search(line) or cls.PHONE_PATTERN.search(line):
                continue
            lower_line = line.lower()
            if any(term in lower_line for term in ["resume", "curriculum", "vitae", "profile", "page"]):
                continue
            if len(line) < 40 and re.match(r"^[A-Za-z\s\.\'-]+$", line):
                return line.strip()

        return lines[0][:40].strip() if lines else fallback

    @classmethod
    def extract_email(cls, raw_text: Optional[str]) -> str:
        """Extracts email address using regex."""
        if not raw_text:
            return ""
        match = cls.EMAIL_PATTERN.search(raw_text)
        return match.group(0) if match else ""

    @classmethod
    def extract_phone(cls, raw_text: Optional[str]) -> str:
        """Extracts phone number using regex."""
        if not raw_text:
            return ""
        match = cls.PHONE_PATTERN.search(raw_text)
        return match.group(0) if match else ""

    @classmethod
    def extract_sections(cls, raw_text: Optional[str]) -> Dict[str, str]:
        """Segments resume into recognized sections (skills, experience, education, etc.)."""
        if not raw_text:
            return {}

        sections: Dict[str, List[str]] = {"general": []}
        current_section = "general"

        for line in raw_text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue

            # Check if line is a section header (short line, <= 45 chars)
            header_candidate = stripped.rstrip(":")
            if len(header_candidate) <= 45:
                matched_sec = None
                for sec_name, pattern in cls.SECTION_PATTERNS.items():
                    if pattern.match(header_candidate):
                        matched_sec = sec_name
                        break

                if matched_sec:
                    current_section = matched_sec
                    if current_section not in sections:
                        sections[current_section] = []
                    continue

            sections[current_section].append(stripped)

        return {sec: "\n".join(lines) for sec, lines in sections.items() if lines}

    @classmethod
    def extract_skills(cls, raw_text: Optional[str]) -> List[str]:
        """Extracts and normalizes skills found anywhere in the resume text."""
        if not raw_text:
            return []

        tokens = set(TextCleaner.extract_words(raw_text))
        cleaned_text = TextCleaner.clean_text(raw_text)
        found_skills: List[str] = []

        for skill in SkillNormalizer.TECH_SKILLS_VOCAB:
            skill_cleaned = skill.lower()
            if " " in skill_cleaned:
                pattern = r"\b" + re.escape(skill_cleaned) + r"\b"
                if re.search(pattern, cleaned_text):
                    found_skills.append(skill)
            else:
                if skill_cleaned == "react":
                    # Disambiguate React (web) from React Native (mobile)
                    text_without_rn = re.sub(r"\breact\s+native\b", "", cleaned_text)
                    tokens_without_rn = set(TextCleaner.extract_words(text_without_rn))
                    if any(t in tokens_without_rn for t in ["react", "react.js", "reactjs"]):
                        found_skills.append(skill)
                else:
                    if skill_cleaned in tokens:
                        found_skills.append(skill)

        return SkillNormalizer.normalize_list(found_skills)

    @classmethod
    def extract_experience_years(cls, raw_text: Optional[str]) -> float:
        """Extracts total stated years of experience."""
        if not raw_text:
            return 0.0

        text = raw_text.lower()
        explicit_years = 0.0
        patterns = [
            r"(\d+(?:\.\d+)?)\s*(?:to|-)\s*\d+(?:\.\d+)?\s*year[s]?",
            r"(\d+(?:\.\d+)?)\s*(?:\+|-)?\s*year[s]?\s*(?:of\s*)?experience",
            r"experience\s*(?:of\s*)?(?:at\s*least\s*)?(\d+(?:\.\d+)?)\s*year[s]?",
            r"(\d+(?:\.\d+)?)\s*\+\s*years\b"
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                try:
                    explicit_years = float(matches[0])
                    break
                except (ValueError, IndexError):
                    continue

        # Look for date ranges like "Jan 2020 - Mar 2023" or "2019 to Present"
        date_pattern = re.compile(
            r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december)?\s*"
            r"(20\d{2})\s*(?:-|to|–|—)\s*"
            r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december|present|current|now)?\s*"
            r"(20\d{2})?",
            re.IGNORECASE
        )
        
        parsed_years = 0.0
        for match in date_pattern.findall(text):
            start_year_str, end_year_str = match
            try:
                start_year = int(start_year_str)
                end_year = int(end_year_str) if end_year_str else 2024
                
                diff = end_year - start_year
                if 0 < diff < 15:
                    parsed_years += diff
            except:
                continue

        return max(explicit_years, parsed_years)

    @classmethod
    def parse_resume(cls, filename: str, raw_text: Optional[str]) -> Resume:
        """
        Parses raw resume text into a rich Resume model.
        Extracts sections, contact information, and skills without hallucinating
        unsupported structured records.
        """
        if raw_text is None:
            raw_text = ""

        cleaned_text = TextCleaner.clean_text(raw_text)
        candidate_name = cls.extract_name(raw_text, fallback=filename.replace(".pdf", ""))
        email = cls.extract_email(raw_text)
        phone = cls.extract_phone(raw_text)
        sections = cls.extract_sections(raw_text)
        skills = cls.extract_skills(raw_text)
        experience_years = cls.extract_experience_years(raw_text)

        # Do not hallucinate detailed experience_entries or project entries:
        # they remain empty lists until reliable parsers are implemented,
        # while sections preserve the authentic source text.
        return Resume(
            filename=filename,
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            candidate_name=candidate_name,
            email=email,
            phone=phone,
            skills=skills,
            experience_years=experience_years,
            sections=sections,
            experience_entries=[],
            projects=[],
            education=[],
            certifications=[]
        )
