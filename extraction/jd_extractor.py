import re
from typing import List, Dict, Tuple, Optional, Set
from app.models import JobDescription, SkillEvidence
from ingestion.text_cleaner import TextCleaner
from extraction.skill_normalizer import SkillNormalizer

class JDExtractor:
    """
    Extracts structured information from Job Descriptions.
    Implements multi-tier skill classification:
    - required_skills: mandatory/must-have skills backed by strong evidence
    - preferred_skills: nice-to-have/bonus skills
    - contextual_skills: technologies mentioned without explicit requirement cues
    
    Retains source snippets, confidence scores, and cue triggers in SkillEvidence.
    """

    # Comprehensive vocabulary of tech skills to search for
    TECH_SKILLS_VOCAB = [
        # Languages
        "python", "javascript", "typescript", "java", "c++", "c#", ".net", "go", "ruby", "php", "swift", "kotlin", "rust",
        # Frontend
        "react", "react native", "angular", "vue", "next.js", "svelte", "jquery", "bootstrap", "tailwind", "html", "css",
        # Backend & Frameworks
        "node.js", "express", "django", "flask", "fastapi", "spring boot", "laravel", "rails",
        # Databases & Caching
        "mongodb", "postgresql", "mysql", "redis", "sqlite", "sql server", "dynamodb",
        # Cloud & DevOps
        "aws", "azure", "gcp", "docker", "kubernetes", "git", "ci/cd", "jenkins", "terraform",
        # APIs & Architecture
        "rest api", "graphql", "grpc", "microservices",
        # Methodologies & Tools
        "agile", "scrum"
    ]

    # Section header regex patterns
    REQUIRED_SECTION_PATTERN = re.compile(
        r"^(?:(?:minimum|basic|key|core|mandatory|role)\s+)?(?:requirements|qualifications|skills|requirements\s*&?\s*skills)\s*$|"
        r"^what\s+(?:you['’]ll\s+need|you\s+need|we['’]re\s+looking\s+for)\s*$|"
        r"^must\s+have[s]?\s*$|"
        r"^eligibility(?:\s+criteria)?\s*$",
        re.IGNORECASE
    )

    PREFERRED_SECTION_PATTERN = re.compile(
        r"^(?:preferred|desired|additional|optional|bonus)(?:\s+(?:qualifications|skills|requirements))?\s*$|"
        r"^nice\s+to\s+have[s]?\s*$|"
        r"^good\s+to\s+have[s]?\s*$|"
        r"^bonus(?:\s+(?:points|qualifications))?\s*$|"
        r"^pluses\s*$",
        re.IGNORECASE
    )

    # In-sentence cue phrases
    PREFERRED_CUES = [
        "nice to have", "preferred", "bonus", "bonus point", "familiarity with",
        "good to have", "plus", "an advantage", "desired", "optional",
        "exposure to", "basic understanding of", "basic knowledge of"
    ]

    REQUIRED_CUES = [
        "must have", "must possess", "required", "mandatory", "essential",
        "minimum of", "strong proficiency in", "strong proficiency", "proficiency in",
        "proficient in", "strong knowledge of", "deep understanding of",
        "hands-on experience with", "proven experience with", "experience with"
    ]

    @classmethod
    def extract_title(cls, raw_text: Optional[str]) -> str:
        """Attempts to extract the job title from the first few non-empty lines of raw text."""
        if not raw_text or not raw_text.strip():
            return "Unknown Job Title"

        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
        if not lines:
            return "Unknown Job Title"

        for line in lines[:4]:
            lower_line = line.lower()
            if any(word in lower_line for word in [
                "developer", "engineer", "intern", "internship", "analyst",
                "designer", "architect", "programmer", "consultant", "lead"
            ]):
                if len(line) < 80:
                    return line
        return lines[0][:60]

    @classmethod
    def extract_required_experience(cls, raw_text: Optional[str]) -> float:
        """
        Extracts required experience in years using regex.
        Supports patterns like '3+ years', 'at least 2 years', '0-1 years', etc.
        """
        if not raw_text:
            return 0.0

        text = raw_text.lower()
        patterns = [
            r"(\d+(?:\.\d+)?)\s*(?:to|-)\s*\d+(?:\.\d+)?\s*year[s]?",
            r"(\d+(?:\.\d+)?)\s*(?:\+|-)?\s*year[s]?\s*(?:of\s*)?experience",
            r"experience\s*(?:of\s*)?(?:at\s*least\s*)?(\d+(?:\.\d+)?)\s*year[s]?",
            r"minimum\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*year[s]?"
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                try:
                    return float(matches[0])
                except (ValueError, IndexError):
                    continue
        return 0.0

    @classmethod
    def segment_sections(cls, raw_text: str) -> Dict[str, str]:
        """Segments JD text into logical sections based on detected headers."""
        sections: Dict[str, List[str]] = {"general": []}
        current_section = "general"

        for line in raw_text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue

            # Header detection (usually short lines, < 50 chars, optionally ending with :)
            header_candidate = stripped.rstrip(":")
            if len(header_candidate) < 50:
                if cls.PREFERRED_SECTION_PATTERN.match(header_candidate):
                    current_section = "preferred"
                    if current_section not in sections:
                        sections[current_section] = []
                    continue
                elif cls.REQUIRED_SECTION_PATTERN.match(header_candidate):
                    current_section = "required"
                    if current_section not in sections:
                        sections[current_section] = []
                    continue
                elif any(header_candidate.lower().startswith(p) for p in ["about", "responsibilities", "overview", "who we are"]):
                    current_section = "contextual"
                    if current_section not in sections:
                        sections[current_section] = []
                    continue

            sections[current_section].append(stripped)

        return {sec: "\n".join(lines) for sec, lines in sections.items() if lines}

    @classmethod
    def _find_matching_skills_in_text(cls, text: str) -> List[Tuple[str, str]]:
        """
        Finds occurrences of vocabulary skills in a text snippet.
        Returns list of (canonical_skill, matched_raw_string).
        """
        tokens = set(TextCleaner.extract_words(text))
        cleaned_text = TextCleaner.clean_text(text)
        found: List[Tuple[str, str]] = []

        for skill in cls.TECH_SKILLS_VOCAB:
            skill_cleaned = skill.lower()
            if " " in skill_cleaned:
                pattern = r"\b" + re.escape(skill_cleaned) + r"\b"
                if re.search(pattern, cleaned_text):
                    canonical = SkillNormalizer.normalize(skill)
                    found.append((canonical, skill))
            else:
                if skill_cleaned == "react":
                    text_without_rn = re.sub(r"\breact\s+native\b", "", cleaned_text)
                    tokens_without_rn = set(TextCleaner.extract_words(text_without_rn))
                    if any(t in tokens_without_rn for t in ["react", "react.js", "reactjs"]):
                        canonical = SkillNormalizer.normalize(skill)
                        found.append((canonical, skill))
                else:
                    if skill_cleaned in tokens:
                        canonical = SkillNormalizer.normalize(skill)
                        found.append((canonical, skill))

        return found

    @classmethod
    def extract_and_classify_skills(cls, raw_text: Optional[str]) -> Tuple[List[str], List[str], List[str], Dict[str, SkillEvidence]]:
        """
        Extracts skills and classifies them into:
        - required_skills
        - preferred_skills
        - contextual_skills
        
        Returns (required_skills, preferred_skills, contextual_skills, skill_evidences).
        Preserves uncertainty: if not backed by explicit requirement cues or sections,
        the skill is classified as contextual.
        """
        if not raw_text or not raw_text.strip():
            return [], [], [], {}

        sections = cls.segment_sections(raw_text)
        evidences: Dict[str, SkillEvidence] = {}

        # Priority values: required (3) > preferred (2) > contextual (1)
        priority_map = {"required": 3, "preferred": 2, "contextual": 1}

        # Process each section line by line
        for section_name, section_content in sections.items():
            for line in section_content.split("\n"):
                line_stripped = line.strip()
                if not line_stripped:
                    continue

                line_lower = line_stripped.lower()
                matched_skills = cls._find_matching_skills_in_text(line_stripped)

                if not matched_skills:
                    continue

                # Determine in-sentence cue
                has_pref_cue = any(cue in line_lower for cue in cls.PREFERRED_CUES)
                has_req_cue = any(cue in line_lower for cue in cls.REQUIRED_CUES)

                # Classification logic
                if has_pref_cue:
                    classification = "preferred"
                    cue_phrase = next(c for c in cls.PREFERRED_CUES if c in line_lower)
                    confidence = 0.90
                elif has_req_cue:
                    classification = "required"
                    cue_phrase = next(c for c in cls.REQUIRED_CUES if c in line_lower)
                    confidence = 0.90
                elif section_name == "preferred":
                    classification = "preferred"
                    cue_phrase = "section:preferred"
                    confidence = 0.85
                elif section_name == "required":
                    classification = "required"
                    cue_phrase = "section:required"
                    confidence = 0.85
                else:
                    # Uncertainty preserved: contextual mention
                    classification = "contextual"
                    cue_phrase = "contextual_mention"
                    confidence = 0.50

                for canonical_skill, raw_match in matched_skills:
                    current_prio = priority_map.get(classification, 1)
                    existing_evidence = evidences.get(canonical_skill)

                    if existing_evidence is None:
                        evidences[canonical_skill] = SkillEvidence(
                            skill=canonical_skill,
                            classification=classification,
                            confidence=confidence,
                            source_context=line_stripped[:200],
                            cue_phrase=cue_phrase
                        )
                    else:
                        existing_prio = priority_map.get(existing_evidence.classification, 1)
                        # Upgrade if current classification has higher evidence priority
                        if current_prio > existing_prio:
                            evidences[canonical_skill] = SkillEvidence(
                                skill=canonical_skill,
                                classification=classification,
                                confidence=confidence,
                                source_context=line_stripped[:200],
                                cue_phrase=cue_phrase
                            )

        # Segregate into lists
        required = sorted([s for s, ev in evidences.items() if ev.classification == "required"])
        preferred = sorted([s for s, ev in evidences.items() if ev.classification == "preferred"])
        contextual = sorted([s for s, ev in evidences.items() if ev.classification == "contextual"])

        return required, preferred, contextual, evidences

    @classmethod
    def parse_jd(cls, filename: str, raw_text: Optional[str]) -> JobDescription:
        """Parses raw text and returns a fully populated JobDescription model."""
        if raw_text is None:
            raw_text = ""

        cleaned_text = TextCleaner.clean_text(raw_text)
        title = cls.extract_title(raw_text)
        required, preferred, contextual, evidences = cls.extract_and_classify_skills(raw_text)
        exp_required = cls.extract_required_experience(raw_text)
        sections = cls.segment_sections(raw_text)

        return JobDescription(
            filename=filename,
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            title=title,
            required_skills=required,
            preferred_skills=preferred,
            contextual_skills=contextual,
            skill_evidences=evidences,
            experience_years_required=exp_required,
            sections=sections
        )
