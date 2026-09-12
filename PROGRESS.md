# Project Progress & Architectural Status

## 1. Current Architectural Status

The system foundation, keyword matching engine, and semantic matching engine are fully implemented, thoroughly tested, and verified.
**`keyword_score` and `semantic_score` are currently independent components.**
The final hybrid ranker has NOT been built yet, and weights remain strictly provisional.

---

## 2. Phase 3 — Semantic Matching Engine Implementation

### Files Created / Changed
- [`app/matching/semantic_matcher.py`](file:///c:/Users/KIIT0001/Documents/GitHub/Hackathon/app/matching/semantic_matcher.py) *(NEW)*: `SemanticMatcher` implementation with section-aware decomposition, local sentence embeddings, noise-floor calibration, and explainable evidence.
- [`app/matching/__init__.py`](file:///c:/Users/KIIT0001/Documents/GitHub/Hackathon/app/matching/__init__.py): Exported `SemanticMatcher` alongside `KeywordMatcher`.
- [`tests/test_semantic_matcher.py`](file:///c:/Users/KIIT0001/Documents/GitHub/Hackathon/tests/test_semantic_matcher.py) *(NEW)*: Comprehensive unit, integration, and benchmark test suite (21 new test cases covering all semantic matching requirements).

---

## 3. Semantic Matcher Architecture & Strategy

### 1. Local Embedding Model Lifecycle
- **Model**: `all-MiniLM-L6-v2` loaded via `sentence-transformers`.
- **Dimensions**: 384-dimensional dense vectors.
- **Offline Guarantee**: Runs completely locally on CPU without requiring external APIs (Gemini, OpenAI) or active internet connection during scoring.
- **Singleton Loader**: `SemanticMatcher.get_model()` loads model weights once in memory and reuses them across all candidates and batches.
- **Embedding Cache**: `_embedding_cache` stores text-to-vector mappings in memory, eliminating redundant forward passes for identical text chunks.

### 2. Section-Aware Chunking Strategy
Avoids naive whole-document similarity. Decomposes both documents into fine-grained, contextual units:

- **JD-Side Semantic Requirement Chunks**:
  - `required` (Weight: 1.0): Must-have skills and mandatory qualification bullets from `jd.skill_evidences`, `jd.sections["required"]`, or explicit requirements.
  - `responsibilities` (Weight: 0.85): Core role responsibilities and day-to-day duties from `jd.sections["contextual"]` or overview descriptions.
  - `preferred` (Weight: 0.50): Desirable qualifications and nice-to-have skills from `jd.sections["preferred"]`.
  - `general` (Weight: 0.30): High-level role title and background overview.

- **Resume-Side Semantic Evidence Chunks**:
  - `experience`: Individual role titles, company names, project descriptions, and duty bullet points.
  - `projects`: Project names, descriptions, technical achievements, and technologies used.
  - `skills`: Grouped technical skills and domain proficiencies.
  - `summary`: Professional headline and objective statements.
  - `education` / `certifications`: Academic credentials and professional certifications.

- **Fidelity**: Preserves exact source text casing, typographical quotation marks, and line structures for auditability.

### 3. Calibrated Similarity & Score Aggregation Formula

1. **Cosine Similarity Matrix**:
   Given $M$ JD requirement chunks with embeddings $\mathbf{E}_Q$ and $N$ candidate evidence chunks with embeddings $\mathbf{E}_R$:
   $$\mathbf{C}_{i, j} = \mathbf{E}_{Q, i} \cdot \mathbf{E}_{R, j}^T$$

2. **Best Match Identification**:
   For each JD requirement $i \in \{0, \dots, M-1\}$, find its strongest candidate match:
   $$j^*(i) = \arg\max_j \mathbf{C}_{i, j}, \quad \text{raw\_sim}_i = \mathbf{C}_{i, j^*(i)}$$

3. **Noise-Floor Calibration**:
   To prevent unrelated candidate backgrounds from accumulating false-positive scores from generic English sentence overlap, a calibrated noise threshold ($\tau_{\text{base}} = 0.15$) is applied:
   $$s(q_i) = \begin{cases} 0.0, & \text{if } \text{raw\_sim}_i \le \tau_{\text{base}} \\ \min\left(1.0, \frac{\text{raw\_sim}_i - \tau_{\text{base}}}{1.0 - \tau_{\text{base}}}\right), & \text{if } \text{raw\_sim}_i > \tau_{\text{base}} \end{cases}$$

4. **Weighted Score Aggregation**:
   The candidate's final semantic score is aggregated across all JD requirement chunks using their section weights $w_i$:
   $$\text{semantic\_score} = \text{round}\left(\frac{\sum_{i=0}^{M-1} w_i \cdot s(q_i)}{\sum_{i=0}^{M-1} w_i}, 4\right)$$

5. **Properties**:
   - Strictly bounded within $[0.0, 1.0]$.
   - Deterministic and candidate-independent (candidate score does not shift when other candidates are added or removed).
   - Immune to dilution from irrelevant resume sections.

---

## 4. Semantic Evidence & Explainability

Populates `SemanticScoreBreakdown` inside `CandidateResult`:

- **Strongest Matches (`strongest_matches`)**: Top 5 highest-value matches linking exact JD requirements to explicit resume evidence:
  ```json
  {
    "jd_chunk": "Develop scalable backend APIs and web services using Python.",
    "jd_section": "required",
    "resume_chunk": "Built Python microservices and HTTP APIs.",
    "resume_section": "experience",
    "similarity": 0.6800,
    "raw_similarity": 0.7280
  }
  ```
- **Section Breakdown (`similarity_evidence`)**: Granular section subscores, evaluated chunk counts, and calibration threshold:
  ```json
  {
    "section_scores": {
      "required": 0.6800,
      "responsibilities": 0.5210,
      "preferred": 0.4500,
      "general": 0.3500
    },
    "jd_chunks_evaluated": 7,
    "resume_chunks_evaluated": 12,
    "noise_threshold": 0.15,
    "all_matches_count": 7
  }
  ```

---

## 5. Batch Processing API

- `SemanticMatcher.match_batch(jd, candidates, config)`:
  1. Decomposes JD into chunks once.
  2. Decomposes all candidate resumes in the batch into chunks.
  3. Batch-encodes all unique JD and candidate texts in single passes through the model.
  4. Computes similarity matrices via PyTorch/numpy dot products.
  5. Returns `List[CandidateResult]` sorted descending by `semantic_score`.

---

## 6. Test Suite & Verification Results

Executed full pytest suite:
```bash
python -m pytest -v tests
```

**Results: 73 passed in 24.67s (100% pass rate)**

```
tests/test_edge_cases.py (5 passed)
tests/test_false_positives.py (4 passed)
tests/test_jd_extractor.py (6 passed)
tests/test_keyword_matcher.py (22 passed)
tests/test_models_and_config.py (2 passed)
tests/test_resume_extractor.py (3 passed)
tests/test_semantic_matcher.py (21 passed)
  - test_relevant_vs_irrelevant_resume
  - test_paraphrased_experience_without_exact_keywords
  - test_unrelated_experience_scores_substantially_lower
  - test_experience_and_projects_contribute
  - test_irrelevant_sections_do_not_dominate
  - test_missing_sections_do_not_crash
  - test_low_keyword_high_semantic_paraphrase
  - test_high_keyword_weak_semantic_keyword_stuffing
  - test_unrelated_domains_low_semantic_score
  - test_professional_jargon_alone_does_not_yield_high_score
  - test_empty_jd
  - test_empty_resume
  - test_whitespace_only
  - test_very_short_text
  - test_duplicated_sections_deduplication
  - test_special_characters_and_formatting
  - test_evidence_structure_and_provenance
  - test_synthetic_candidates_relative_ordering
  - test_batch_matches_single_match
  - test_candidate_independence
  - test_18_resumes_batch_smoke_test
tests/test_skill_normalizer.py (5 passed)
tests/test_text_cleaner.py (5 passed)
```

### Performance Benchmark (1 JD + 18 Resumes)
- **Batch Execution Latency**: **0.143 – 0.155 seconds** total on CPU.
- **Memory Consumption**: Single model weight instance (~90MB) shared in-process.

---

## 7. Keyword & Semantic Independence Verification

The test suite explicitly proves that keyword matching and semantic matching operate independently:
1. **Low Keyword, High Semantic**: A candidate describing "Built HTTP services and backend endpoints for production web systems" against "Develop REST APIs" scores:
   - `keyword_score` = 0.0000
   - `semantic_score` = 0.2395
2. **High Keyword, Weak Semantic**: A candidate who stuffs "Python" into their skills list with trivial hello-world experience scores:
   - `keyword_score` = 0.7000 (100% of required skills matched)
   - `semantic_score` = 0.2800 (low contextual alignment with complex distributed backend requirements)

---

## 8. Remaining Limitations

1. **Independent Scoring Only**:
   Keyword scores and semantic scores are currently isolated. The hybrid ranking formula combining them into `final_score` is intentionally not yet implemented.
2. **Experience Penalties Isolated**:
   Experience duration gaps (e.g. candidate with 1 year applying for 3+ years role) are extracted but not yet applied as penalties to the final score.
3. **Weight Calibration**:
   The provisional weights (`keyword_weight: 0.40`, `semantic_weight: 0.60`) remain uncalibrated until hybrid evaluation is developed.

---

## 9. Next Recommended Task

- **Phase 4 — Hybrid Ranking Engine, Experience Penalties, and Calibration**:
  - Implement `HybridRanker` combining `KeywordMatcher`, `SemanticMatcher`, and `PenaltyCalculator`.
  - Apply experience gap penalties with transparent deductions.
  - Produce comprehensive, human-auditable ranking explanations (`ranking_reason`).
  - Verify hybrid calibration against diverse candidate batches.
