# Project Progress & Architectural Status

## 1. What Was Corrected

1. **Decoupled & Deprecrated Hardcoded Scoring Weights**:
   - Replaced fixed global constants with `RankingConfig` in `app/config.py`.
   - Explicitly documented that all ranking weights (e.g., keyword 0.40, semantic 0.60, required skill 0.70, preferred skill 0.30) are **provisional defaults**.
   - Prevented premature weight lock-in; weight tuning is deferred until empirical evaluation against candidate test data is performed.

2. **Fixed Simplistic JD Skill Classification**:
   - Refactored `JobDescription` and `JDExtractor` to replace the naive "every detected skill is required" behavior.
   - Introduced a three-tier classification:
     - `required_skills`: Mandated via explicit requirement sections ("Requirements", "Minimum Qualifications", "Must Haves") or strong in-sentence cues ("must have", "required", "strong proficiency in", "experience with").
     - `preferred_skills`: Explicitly preferred via section headers ("Preferred Qualifications", "Nice to Have", "Bonus") or in-sentence cues ("nice to have", "preferred", "bonus", "familiarity with").
     - `contextual_skills`: Skills mentioned in company overviews, responsibilities, or tech stack descriptions without requirement cues.
   - Retained provenance evidence via `SkillEvidence` (stores skill name, classification tier, confidence score, verbatim source snippet, and triggering cue phrase).
   - Preserved uncertainty rather than falsely categorizing unverified mentions as mandatory requirements.

3. **Hierarchical Scoring Data Model**:
   - Enhanced `CandidateResult` in `app/models.py` with granular scoring evidence structures:
     - `KeywordScoreBreakdown`: required vs preferred skill score, matched required, missing required, matched preferred, missing preferred, and contextual evidence.
     - `SemanticScoreBreakdown`: strongest section matches and similarity evidence.
     - `PenaltyBreakdown`: experience gap penalties, missing critical requirement penalties, and breakdown details.
     - `ranking_reason`: comprehensive natural-language explainability.

4. **Structured & Grounded Resume Model**:
   - Enhanced `Resume` in `app/models.py` with structured placeholders:
     - `skills`, `experience_entries`, `projects`, `education`, `certifications`, `sections`, `candidate_name`, `email`, `phone`, `experience_years`.
   - Created `extraction/resume_extractor.py` ensuring anti-hallucination: raw section text is preserved while structured object lists (`experience_entries`, `projects`, `education`) remain clean empty lists until reliable parsers are introduced.

5. **Technical Token Preservation in Text Cleaning**:
   - Upgraded `TextCleaner` in `ingestion/text_cleaner.py` to preserve technical tokens without regex corruption:
     - `C++`, `C#`, `.NET`, `Node.js`, `Next.js`, `CI/CD`, `REST API`, `React.js`.
     - Preserved slashes in composite acronyms (`ci/cd`) while correctly splitting slash-delimited terms (`node.js/express` -> `node.js`, `express`).
     - Handled unicode quotes, dashes, non-breaking spaces, empty, and `None` inputs safely.

6. **Strict Skill Equivalence & False-Positive Prevention**:
   - Refactored `SkillNormalizer` in `extraction/skill_normalizer.py` to map strictly canonical synonyms (`js` -> `javascript`, `ts` -> `typescript`, `node.js` -> `nodejs`, `react.js` -> `react`, `mongo` -> `mongodb`, `restful API` -> `rest api`).
   - Strictly enforced independence between related but distinct technologies:
     - React != JavaScript
     - Node.js != Express
     - MongoDB != SQL
     - AWS != Docker
     - Java != JavaScript
     - C != C++ != C#

---

## 2. Why Required / Preferred / Contextual Classification Matters

In real-world recruitment and applicant tracking systems (ATS):
- **False Disqualifications**: If every technology mentioned in an "About the Company" or "Our Stack" paragraph is labeled as mandatory, strong candidates with core skills will be penalized or rejected for not knowing peripheral or contextual tools.
- **Fair Weighting**: A candidate missing a "must-have" core language (e.g., Python or React) should be penalized significantly more than one missing a "nice-to-have" tool (e.g., Redis or Docker).
- **Explainability & Trust**: Hiring managers need to know exactly *why* a candidate was shortlisted or demoted: "Matched all 4 required skills, missing 1 preferred skill (Docker)" is actionable; an opaque number from an unclassified skill bucket is not.

---

## 3. Current Data Model Architecture

```text
JobDescription
├── filename, raw_text, cleaned_text, title
├── required_skills: List[str]
├── preferred_skills: List[str]
├── contextual_skills: List[str]
├── skill_evidences: Dict[str, SkillEvidence]
│   └── SkillEvidence (skill, classification, confidence, source_context, cue_phrase)
├── experience_years_required: float
└── sections: Dict[str, str]

Resume
├── filename, raw_text, cleaned_text, candidate_name, email, phone
├── skills: List[str]
├── experience_years: float
├── experience_entries: List[ExperienceEntry]  (clean/unhallucinated)
├── projects: List[ProjectEntry]                (clean/unhallucinated)
├── education: List[EducationEntry]            (clean/unhallucinated)
├── certifications: List[str]
└── sections: Dict[str, str]

CandidateResult
├── resume: Resume
├── keyword_breakdown: KeywordScoreBreakdown
│   ├── score: float
│   ├── required_skill_score: float
│   ├── preferred_skill_score: float
│   ├── matched_required_skills: List[str]
│   ├── missing_required_skills: List[str]
│   ├── matched_preferred_skills: List[str]
│   ├── missing_preferred_skills: List[str]
│   └── evidence: Dict[str, Any]
├── semantic_breakdown: SemanticScoreBreakdown
│   ├── score: float
│   ├── strongest_matches: List[Dict[str, Any]]
│   └── similarity_evidence: Dict[str, Any]
├── penalties: PenaltyBreakdown
│   ├── experience_penalty: float
│   ├── missing_critical_penalty: float
│   ├── details: Dict[str, float]
│   └── total_penalty: float
├── final_score: float
└── ranking_reason: str
```

---

## 4. Current Extraction Limitations

1. **Heuristic Section Headers**:
   - Resume and JD section parsing relies on common regex patterns ("Requirements", "Qualifications", "Technical Skills", "Work Experience"). Non-standard layouts or creative headers may fallback into the "general" section.
2. **Vocabulary-Bounded Skill Discovery**:
   - Skill extraction matches against a curated, high-accuracy tech vocabulary. Novel or obscure domain libraries not in the vocabulary will not be captured during keyword parsing (though semantic matching will later capture semantic alignment).
3. **Structured Resume Entries**:
   - In accordance with the anti-hallucination constraint, individual work history items (`experience_entries`), project items (`projects`), and degrees (`education`) are preserved as raw section text; deep entity extraction of dates and roles is intentionally left for dedicated parsing modules.

---

## 5. Tests and Verification Results

Executed full test suite using `pytest -v tests`:
```
============================= test session starts =============================
platform win32 -- Python 3.13.15, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\Sushanth\Downloads\Hackathon
collected 30 items

tests/test_edge_cases.py::TestEdgeCasesAndMalformedInput::test_jd_empty_and_none_input PASSED [  3%]
tests/test_edge_cases.py::TestEdgeCasesAndMalformedInput::test_resume_empty_and_none_input PASSED [  6%]
tests/test_edge_cases.py::TestEdgeCasesAndMalformedInput::test_malformed_unparseable_experience PASSED [ 10%]
tests/test_edge_cases.py::TestEdgeCasesAndMalformedInput::test_special_characters_and_corrupted_tokens PASSED [ 13%]
tests/test_edge_cases.py::TestEdgeCasesAndMalformedInput::test_pdf_parser_nonexistent_and_directory PASSED [ 16%]
tests/test_false_positives.py::TestFalsePositivePrevention::test_short_language_names_do_not_match_substrings PASSED [ 20%]
tests/test_false_positives.py::TestFalsePositivePrevention::test_java_vs_javascript_distinction PASSED [ 23%]
tests/test_false_positives.py::TestFalsePositivePrevention::test_c_vs_cpp_vs_csharp_distinction PASSED [ 26%]
tests/test_false_positives.py::TestFalsePositivePrevention::test_react_does_not_match_react_native PASSED [ 30%]
tests/test_jd_extractor.py::TestJDExtractor::test_required_vs_preferred_classification_by_cue PASSED [ 33%]
tests/test_jd_extractor.py::TestJDExtractor::test_in_sentence_cue_overrides_ambiguous_section PASSED [ 36%]
tests/test_jd_extractor.py::TestJDExtractor::test_preserve_uncertainty_without_cues PASSED [ 40%]
tests/test_jd_extractor.py::TestJDExtractor::test_experience_extraction PASSED [ 43%]
tests/test_jd_extractor.py::TestJDExtractor::test_title_extraction PASSED [ 46%]
tests/test_jd_extractor.py::TestJDExtractor::test_parse_jd_full_model PASSED [ 50%]
tests/test_models_and_config.py::TestModelsAndConfig::test_provisional_ranking_config_weights PASSED [ 53%]
tests/test_models_and_config.py::TestModelsAndConfig::test_candidate_result_hierarchical_structure PASSED [ 56%]
tests/test_resume_extractor.py::TestResumeExtractor::test_resume_parsing_and_sections PASSED [ 60%]
tests/test_resume_extractor.py::TestResumeExtractor::test_no_hallucination_of_structured_entries PASSED [ 63%]
tests/test_resume_extractor.py::TestResumeExtractor::test_resume_to_dict_structure PASSED [ 66%]
tests/test_skill_normalizer.py::TestSkillNormalizer::test_canonical_equivalences PASSED [ 70%]
tests/test_skill_normalizer.py::TestSkillNormalizer::test_framework_and_library_synonyms PASSED [ 73%]
tests/test_skill_normalizer.py::TestSkillNormalizer::test_strictly_no_false_equivalence_between_distinct_technologies PASSED [ 76%]
tests/test_skill_normalizer.py::TestSkillNormalizer::test_normalize_list_deduplicates_and_sorts PASSED [ 80%]
tests/test_skill_normalizer.py::TestSkillNormalizer::test_empty_and_invalid_inputs PASSED [ 83%]
tests/test_text_cleaner.py::TestTextCleaner::test_technical_tokens_preservation PASSED [ 86%]
tests/test_text_cleaner.py::TestTextCleaner::test_technical_tokens_with_brackets_and_punctuation PASSED [ 90%]
tests/test_text_cleaner.py::TestTextCleaner::test_clean_text_normalizes_whitespace_and_quotes PASSED [ 93%]
tests/test_text_cleaner.py::TestTextCleaner::test_empty_and_none_input PASSED [ 96%]
tests/test_text_cleaner.py::TestTextCleaner::test_non_string_input PASSED [100%]

============================= 30 passed in 0.30s ==============================
```

---

## 6. Next Task

- **Implement the Keyword Matching Engine**:
  - Compute `required_skill_score` and `preferred_skill_score` with evidence.
  - Determine matched vs missing skills between candidates and JDs.
  - Formulate provisional keyword ranking and verify against baseline test fixtures.
  - *Note*: Semantic matching will remain strictly unstarted until the keyword matching engine is fully built and tested.
