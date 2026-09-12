# Project Progress & Architectural Status

## 1. Current Architectural Status

The system foundation and keyword matching engine are fully implemented, thoroughly tested, and verified.
Semantic matching has NOT been started yet and remains strictly decoupled.

---

## 2. Phase 2 — Keyword Matching Engine Implementation

### Files Created / Changed
- [`app/matching/__init__.py`](file:///c:/Users/Sushanth/Downloads/Hackathon/app/matching/__init__.py) *(NEW)*: Package exports for matching modules.
- [`app/matching/keyword_matcher.py`](file:///c:/Users/Sushanth/Downloads/Hackathon/app/matching/keyword_matcher.py) *(NEW)*: `KeywordMatcher` implementation with exact canonical matching, multi-tier scoring, section evidence extraction, and explainable summaries.
- [`extraction/resume_extractor.py`](file:///c:/Users/Sushanth/Downloads/Hackathon/extraction/resume_extractor.py): Added `React Native` disambiguation to prevent mobile framework mentions from falsely triggering web `React` keyword matches.
- [`extraction/jd_extractor.py`](file:///c:/Users/Sushanth/Downloads/Hackathon/extraction/jd_extractor.py): Tightened section header regexes (`REQUIRED_SECTION_PATTERN`, `PREFERRED_SECTION_PATTERN`) to line boundaries so requirement bullet points are not dropped.
- [`tests/test_keyword_matcher.py`](file:///c:/Users/Sushanth/Downloads/Hackathon/tests/test_keyword_matcher.py) *(NEW)*: Comprehensive unit test suite (22 new test cases covering all matching requirements).

---

## 3. Keyword Matching Design & Scoring Formula

### Matching Rules
1. **Canonical Skill Matching**:
   Both JD requirements and candidate profile skills are normalized via `SkillNormalizer` into canonical tokens before matching.
2. **Explicit Skill Evidence**:
   Matches are strictly based on explicit skill mentions. No artificial score boosts or penalties from job titles or experience are conflated into keyword scores.
3. **Strict Non-Equivalence**:
   Related but distinct technologies strictly never count as matches:
   - Java ≠ JavaScript
   - C ≠ C++ ≠ C#
   - React ≠ React Native
   - Node.js ≠ Express
   - MongoDB ≠ SQL
   - AWS ≠ Docker
   - Python ≠ Django

### Scoring Formula
The keyword scoring formula is linear, deterministic, and fully configurable via `RankingConfig`:

$$\text{required\_skill\_score} = \begin{cases} \frac{|\text{matched\_required}|}{|\text{total\_required}|}, & \text{if } |\text{total\_required}| > 0 \\ 0.0, & \text{if } |\text{total\_required}| = 0 \end{cases}$$

$$\text{preferred\_skill\_score} = \begin{cases} \frac{|\text{matched\_preferred}|}{|\text{total\_preferred}|}, & \text{if } |\text{total\_preferred}| > 0 \\ 0.0, & \text{if } |\text{total\_preferred}| = 0 \end{cases}$$

$$\text{keyword\_score} = \text{round}\Big(\min\big(1.0, \max(0.0, \text{required\_skill\_score} \times W_{\text{req}} + \text{preferred\_skill\_score} \times W_{\text{pref}})\big), 4\Big)$$

Where default provisional weights are:
- $W_{\text{req}} = 0.70$ (`RankingConfig.required_skill_weight`)
- $W_{\text{pref}} = 0.30$ (`RankingConfig.preferred_skill_weight`)

#### Zero-Skills Case Handling:
- When a JD has zero required skills (`total_required == 0`), `required_skill_score = 0.0` (candidate has zero requirements to satisfy, preventing unearned credit).
- When a JD has zero preferred skills (`total_preferred == 0`), `preferred_skill_score = 0.0`.

---

## 4. Evidence Behavior & Explainability

Every skill evaluated (both matched and missing) populates `KeywordScoreBreakdown.evidence`:

- **Matched Skill Record**:
  ```json
  {
    "skill": "react",
    "status": "matched",
    "tier": "required",
    "jd_skill": "React.js",
    "candidate_skill": "react",
    "matching_method": "exact_canonical",
    "source_section": "skills",
    "source_context": "...React.js, Node.js, Docker..."
  }
  ```
- **Missing Skill Record**:
  ```json
  {
    "skill": "fastapi",
    "status": "missing",
    "tier": "required",
    "jd_skill": "fastapi",
    "candidate_skill": null,
    "matching_method": "none",
    "source_context": "No explicit skill evidence found in candidate profile"
  }
  ```
- **Ranking Reason**:
  Every candidate receives a human-readable, auditable justification:
  > *"Matched 2/2 required skills (nodejs, react). Matched 1/1 preferred skills (docker). Keyword score: 1.0000 (Required: 1.00 × 0.70, Preferred: 1.00 × 0.30)"*

---

## 5. False-Positive Protections

1. **Token Boundaries**:
   `TextCleaner.extract_words` prevents substring matching:
   - `JavaScript` does not match `Java`.
   - `Ongoing`, `good`, `algorithm` do not match `go`.
   - `Trust`, `frustration` do not match `rust`.
   - `Cloud`, `clean` do not match `c`.
2. **Compound Disambiguation**:
   `React Native` is specifically isolated so that mobile app experience with React Native does not automatically credit web `React`.
3. **Strict Synonym Boundaries**:
   Synonym mapping in `SkillNormalizer` is reserved for true equivalences (`js` → `javascript`, `react.js` → `react`, `restful api` → `rest api`).

---

## 6. Test Suite & Verification Results

Executed full pytest suite:
```bash
python -m pytest -v tests
```

**Results: 52 passed in 0.40s (100% pass rate)**

```
tests/test_edge_cases.py (5 passed)
tests/test_false_positives.py (4 passed)
tests/test_jd_extractor.py (6 passed)
tests/test_keyword_matcher.py (22 passed)
  - test_all_required_skills_matched
  - test_some_required_skills_matched
  - test_no_required_skills_matched
  - test_all_preferred_skills_matched
  - test_partial_preferred_skills_matched
  - test_all_required_and_preferred_matched
  - test_configurable_weights_affect_scores
  - test_java_vs_javascript
  - test_c_vs_cpp
  - test_cpp_vs_csharp
  - test_react_vs_react_native
  - test_node_vs_express
  - test_mongodb_vs_sql
  - test_aws_vs_docker
  - test_python_vs_django
  - test_canonical_synonym_matching
  - test_jd_with_no_required_skills
  - test_jd_with_no_preferred_skills
  - test_resume_with_no_skills
  - test_empty_jd_and_empty_resume
  - test_evidence_structure_and_provenance
  - test_pipeline_with_synthetic_fixtures
tests/test_models_and_config.py (2 passed)
tests/test_resume_extractor.py (3 passed)
tests/test_skill_normalizer.py (5 passed)
tests/test_text_cleaner.py (5 passed)
```

Direct smoke test verification confirmed deterministic batch ranking:
- Candidate Alice (all required + preferred): Score = 1.0000 (Rank 1)
- Candidate Bob (partial required, no preferred): Score = 0.3500 (Rank 2)
- Candidate Charlie (no matching required/preferred): Score = 0.0000 (Rank 3)

---

## 7. Remaining Limitations

1. **Keyword-Only Matching**:
   Does not yet capture semantically equivalent descriptions (e.g. "built scalable web endpoints" for a "REST API" requirement). This is the intended role of the upcoming semantic matching engine.
2. **Vocabulary Scope**:
   Keywords are detected based on the tech vocabulary; novel niche frameworks will rely on the semantic embedding layer.
3. **Experience Separation**:
   Experience years penalties remain unapplied during this keyword-only phase (intentionally isolated as per specification).

---

## 8. Next Recommended Task

- **Phase 3 — Build and Verify the Semantic Matching Engine**:
  - Implement sentence/document embedding generation using the lightweight CPU model (`all-MiniLM-L6-v2`).
  - Calculate cosine similarities between JD sections and resume text/sections.
  - Populate `SemanticScoreBreakdown` (strongest section matches, similarity evidence).
  - Test semantic matching in isolation before combining into the final hybrid ranker.
