import re
from typing import List, Dict, Any, Optional, Set, Tuple
from app.config import RankingConfig, DEFAULT_RANKING_CONFIG
from app.models import (
    JobDescription, Resume, CandidateResult, KeywordScoreBreakdown,
    SemanticScoreBreakdown, PenaltyBreakdown
)
from extraction.skill_normalizer import SkillNormalizer
from extraction.resume_extractor import ResumeExtractor
from ingestion.text_cleaner import TextCleaner

class KeywordMatcher:
    """
    Evaluates explicit keyword and skill alignment between a Candidate Resume
    and a Job Description.
    
    Principles:
    1. Canonical Skill Matching: Uses SkillNormalizer to compare canonical skill tokens
       rather than naive substring searches.
    2. Strict Non-Equivalence: Disallows related technologies from falsely matching
       (e.g., Java != JavaScript, C != C++, C++ != C#, React != React Native, Node.js != Express).
    3. Multi-tier Scoring: Separates required vs. preferred skill compliance according to
       configurable weights in RankingConfig.
    4. Full Provenance & Explainability: Retains inspectable evidence for every matched and
       missing skill, including source section and textual snippets.
    5. Zero Artificial Boosting: Years of experience, job titles, or fuzzy heuristics
       are NOT mixed into the keyword matching score.
    """

    @classmethod
    def _find_skill_in_sections(cls, canonical_skill: str, resume: Resume) -> Tuple[str, str]:
        """
        Locates the resume section and textual snippet that provides evidence
        for a matched skill.
        Returns (section_name, source_snippet).
        """
        if not resume.sections and not resume.raw_text:
            return "general", f"Candidate explicit skill: {canonical_skill}"

        # Priority search order across sections
        section_priority = ["skills", "experience", "projects", "education", "summary", "general"]
        
        # Build search patterns for the canonical skill and known variants
        # e.g., for 'c++', match 'c++'; for 'ci/cd', match 'ci/cd'; for 'nodejs', match 'node.js' or 'nodejs'
        search_terms = [canonical_skill]
        for raw, canon in SkillNormalizer.SYNONYMS_MAP.items():
            if canon == canonical_skill:
                search_terms.append(raw)
        search_terms = list(dict.fromkeys(search_terms))

        # Check prioritized sections
        for sec_name in section_priority:
            content = resume.sections.get(sec_name, "")
            if not content:
                continue

            for term in search_terms:
                pattern = r"(?:^|[^\w])" + re.escape(term) + r"(?:[^\w]|$)"
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    # Extract snippet around match
                    start = max(0, match.start() - 40)
                    end = min(len(content), match.end() + 60)
                    snippet = content[start:end].strip().replace("\n", " ")
                    return sec_name, f"...{snippet}..."

        # Fallback to searching entire raw text if section wasn't mapped
        if resume.raw_text:
            for term in search_terms:
                pattern = r"(?:^|[^\w])" + re.escape(term) + r"(?:[^\w]|$)"
                match = re.search(pattern, resume.raw_text, re.IGNORECASE)
                if match:
                    start = max(0, match.start() - 40)
                    end = min(len(resume.raw_text), match.end() + 60)
                    snippet = resume.raw_text[start:end].strip().replace("\n", " ")
                    return "raw_text", f"...{snippet}..."

        return "profile", f"Explicit candidate skill: {canonical_skill}"

    @classmethod
    def match(
        cls,
        jd: JobDescription,
        resume: Resume,
        config: Optional[RankingConfig] = None
    ) -> CandidateResult:
        """
        Evaluates a single Candidate Resume against a Job Description.
        Populates the keyword_breakdown and explainable ranking_reason of CandidateResult.
        """
        cfg = config or DEFAULT_RANKING_CONFIG

        # 1. Canonicalize and deduplicate JD required skills
        raw_jd_req = jd.required_skills or []
        canonical_req_map: Dict[str, str] = {}
        for s in raw_jd_req:
            norm = SkillNormalizer.normalize(s)
            if norm and norm not in canonical_req_map:
                canonical_req_map[norm] = s
        canonical_req_list = sorted(list(canonical_req_map.keys()))

        # 2. Canonicalize and deduplicate JD preferred skills (excluding any already in required)
        raw_jd_pref = jd.preferred_skills or []
        canonical_pref_map: Dict[str, str] = {}
        for s in raw_jd_pref:
            norm = SkillNormalizer.normalize(s)
            if norm and norm not in canonical_req_map and norm not in canonical_pref_map:
                canonical_pref_map[norm] = s
        canonical_pref_list = sorted(list(canonical_pref_map.keys()))

        # 3. Canonicalize Candidate Skills
        candidate_skills = resume.skills or []
        # If resume skills list is empty but raw_text is available, extract skills deterministically
        if not candidate_skills and resume.raw_text:
            candidate_skills = ResumeExtractor.extract_skills(resume.raw_text)

        candidate_skill_map: Dict[str, str] = {}
        for s in candidate_skills:
            norm = SkillNormalizer.normalize(s)
            if norm and norm not in candidate_skill_map:
                candidate_skill_map[norm] = s
        candidate_canonical_set = set(candidate_skill_map.keys())

        # 4. Perform deterministic matching for Required Skills
        matched_required: List[str] = []
        missing_required: List[str] = []
        evidence: Dict[str, Any] = {}

        for req_skill in canonical_req_list:
            orig_jd_skill = canonical_req_map[req_skill]
            if req_skill in candidate_canonical_set:
                matched_required.append(req_skill)
                orig_cand_skill = candidate_skill_map[req_skill]
                sec_name, snippet = cls._find_skill_in_sections(req_skill, resume)
                evidence[req_skill] = {
                    "skill": req_skill,
                    "status": "matched",
                    "tier": "required",
                    "jd_skill": orig_jd_skill,
                    "candidate_skill": orig_cand_skill,
                    "matching_method": "exact_canonical",
                    "source_section": sec_name,
                    "source_context": snippet
                }
            else:
                missing_required.append(req_skill)
                evidence[req_skill] = {
                    "skill": req_skill,
                    "status": "missing",
                    "tier": "required",
                    "jd_skill": orig_jd_skill,
                    "candidate_skill": None,
                    "matching_method": "none",
                    "source_context": "No explicit skill evidence found in candidate profile"
                }

        # 5. Perform deterministic matching for Preferred Skills
        matched_preferred: List[str] = []
        missing_preferred: List[str] = []

        for pref_skill in canonical_pref_list:
            orig_jd_skill = canonical_pref_map[pref_skill]
            if pref_skill in candidate_canonical_set:
                matched_preferred.append(pref_skill)
                orig_cand_skill = candidate_skill_map[pref_skill]
                sec_name, snippet = cls._find_skill_in_sections(pref_skill, resume)
                evidence[pref_skill] = {
                    "skill": pref_skill,
                    "status": "matched",
                    "tier": "preferred",
                    "jd_skill": orig_jd_skill,
                    "candidate_skill": orig_cand_skill,
                    "matching_method": "exact_canonical",
                    "source_section": sec_name,
                    "source_context": snippet
                }
            else:
                missing_preferred.append(pref_skill)
                evidence[pref_skill] = {
                    "skill": pref_skill,
                    "status": "missing",
                    "tier": "preferred",
                    "jd_skill": orig_jd_skill,
                    "candidate_skill": None,
                    "matching_method": "none",
                    "source_context": "No explicit skill evidence found in candidate profile"
                }

        # 6. Compute Subscores
        total_req = len(canonical_req_list)
        total_pref = len(canonical_pref_list)

        # Zero required skills explicitly handled:
        # If JD specifies 0 required skills, candidate has 0 requirements to satisfy or fail.
        # Required subscore is defined as 0.0 (preventing unearned credit).
        required_skill_score = (len(matched_required) / total_req) if total_req > 0 else 0.0

        # Zero preferred skills explicitly handled:
        # If JD specifies 0 preferred skills, preferred subscore is defined as 0.0.
        preferred_skill_score = (len(matched_preferred) / total_pref) if total_pref > 0 else 0.0

        # 7. Keyword Score Composition
        raw_keyword_score = (
            (required_skill_score * cfg.required_skill_weight) +
            (preferred_skill_score * cfg.preferred_skill_weight)
        )
        # Guarantee normalized score within [0.0, 1.0]
        keyword_score = round(max(0.0, min(1.0, raw_keyword_score)), 4)

        # 8. Build Granular Keyword Breakdown
        keyword_breakdown = KeywordScoreBreakdown(
            score=keyword_score,
            required_skill_score=round(required_skill_score, 4),
            preferred_skill_score=round(preferred_skill_score, 4),
            matched_required_skills=matched_required,
            missing_required_skills=missing_required,
            matched_preferred_skills=matched_preferred,
            missing_preferred_skills=missing_preferred,
            evidence=evidence
        )

        # 9. Formulate Transparent, Explainable Ranking Reason
        explanation_parts = []
        if total_req > 0:
            req_details = f"Matched {len(matched_required)}/{total_req} required skills"
            if matched_required:
                req_details += f" ({', '.join(matched_required)})"
            if missing_required:
                req_details += f"; missing: {', '.join(missing_required)}"
            explanation_parts.append(req_details)
        else:
            explanation_parts.append("No explicit required skills specified in JD")

        if total_pref > 0:
            pref_details = f"Matched {len(matched_preferred)}/{total_pref} preferred skills"
            if matched_preferred:
                pref_details += f" ({', '.join(matched_preferred)})"
            if missing_preferred:
                pref_details += f"; missing: {', '.join(missing_preferred)}"
            explanation_parts.append(pref_details)

        explanation_parts.append(
            f"Keyword score: {keyword_score:.4f} (Required: {required_skill_score:.2f} × {cfg.required_skill_weight:.2f}, "
            f"Preferred: {preferred_skill_score:.2f} × {cfg.preferred_skill_weight:.2f})"
        )
        ranking_reason = ". ".join(explanation_parts)

        # 10. Return Populated CandidateResult
        # Notice: semantic_breakdown and penalties remain in default empty states
        # until their dedicated phases are executed.
        return CandidateResult(
            resume=resume,
            keyword_breakdown=keyword_breakdown,
            semantic_breakdown=SemanticScoreBreakdown(),
            penalties=PenaltyBreakdown(),
            final_score=keyword_score,  # In keyword phase, final score reflects keyword score
            ranking_reason=ranking_reason
        )

    @classmethod
    def match_batch(
        cls,
        jd: JobDescription,
        resumes: List[Resume],
        config: Optional[RankingConfig] = None
    ) -> List[CandidateResult]:
        """
        Evaluates a batch of Candidate Resumes against a Job Description,
        returning results sorted from highest keyword score to lowest keyword score.
        """
        results = [cls.match(jd, resume, config) for resume in resumes]
        # Sort descending by keyword score; tie-break by candidate name for determinism
        results.sort(key=lambda r: (-r.keyword_score, r.resume.candidate_name))
        return results
