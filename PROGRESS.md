# Project Progress & Architectural Status

## 1. Current Architectural Status

The end-to-end backend pipeline — PDF ingestion, text normalization, multi-tier JD/resume extraction, canonical keyword matching, section-aware semantic matching, experience penalty calculation, and hybrid ranking — is **fully implemented, calibrated, and verified**.
All 99 unit, integration, and benchmark tests are passing (100% pass rate).

---

## 2. Phase 4 — Hybrid Ranking, Experience Penalties, and Calibration

### Files Created / Changed
- [`app/matching/penalty_calculator.py`](file:///c:/Users/KIIT0001/Documents/GitHub/Hackathon/app/matching/penalty_calculator.py) *(NEW)*: Dedicated `PenaltyCalculator` evaluating experience gaps with configurable rates and caps.
- [`app/matching/hybrid_ranker.py`](file:///c:/Users/KIIT0001/Documents/GitHub/Hackathon/app/matching/hybrid_ranker.py) *(NEW)*: Orchestrator integrating keyword scoring, semantic scoring, and penalties into `final_score` with complete explainability.
- [`app/config.py`](file:///c:/Users/KIIT0001/Documents/GitHub/Hackathon/app/config.py): Added `experience_penalty_per_year`, `maximum_experience_penalty`, `semantic_noise_threshold`, and `RankingConfig.validate()`.
- [`app/matching/__init__.py`](file:///c:/Users/KIIT0001/Documents/GitHub/Hackathon/app/matching/__init__.py): Exported `PenaltyCalculator` and `HybridRanker`.
- [`tests/test_penalty_calculator.py`](file:///c:/Users/KIIT0001/Documents/GitHub/Hackathon/tests/test_penalty_calculator.py) *(NEW)*: 8 unit tests covering gaps, caps, fresher protection, and malformed inputs.
- [`tests/test_hybrid_ranker.py`](file:///c:/Users/KIIT0001/Documents/GitHub/Hackathon/tests/test_hybrid_ranker.py) *(NEW)*: 18 unit and integration tests covering formulas, config validation, invariants, anti-keyword-stuffing, and the 18-candidate evaluation fixture.

---

## 3. Penalty Architecture & Formula

### 1. Experience Gap Calculation
$$\text{experience\_gap} = \max\big(0.0, \text{jd.experience\_years\_required} - \text{resume.experience\_years}\big)$$

### 2. Penalty Deductions
$$\text{experience\_penalty} = \min\big(\text{experience\_gap} \times \text{cfg.experience\_penalty\_per\_year}, \text{cfg.maximum\_experience\_penalty}\big)$$
$$\text{total\_penalty} = \text{round}\big(\min(1.0, \max(0.0, \text{experience\_penalty})) , 4\big)$$

- **Provisional Default Parameters**:
  - `experience_penalty_per_year = 0.05` (5% deduction per year of experience deficit).
  - `maximum_experience_penalty = 0.20` (capped at 20% maximum deduction).
- **Fresher & Student Protection**:
  - For entry-level ($0\text{--}1$ year) roles, the penalty is minor ($0.00 \text{ to } 0.05$).
  - The $0.20$ maximum cap guarantees that an exceptional student or career-switcher with high skill and semantic alignment can remain competitive against experienced candidates.
- **Explainability**:
  - Exposes exact numeric gaps, rates, and caps in `PenaltyBreakdown.details`.

---

## 4. Hybrid Ranking Engine Architecture

```
                      Job Description + Resume
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
   KeywordMatcher         SemanticMatcher         PenaltyCalculator
  (exact canonical)      (section embeddings)     (experience gap)
         │                       │                       │
         ▼                       ▼                       ▼
   keyword_score           semantic_score          total_penalty
   (weight: 0.40)          (weight: 0.60)                │
         │                       │                       │
         └───────────────┬───────┘                       │
                         ▼                               │
                     base_score                          │
                         │                               │
                         └───────────────┬───────────────┘
                                         ▼
                                   HybridRanker
                                         │
                                         ▼
                                    final_score
                                  ranking_reason
```

### 1. Hybrid Formula
$$\text{base\_score} = (\text{keyword\_score} \times W_{\text{kw}}) + (\text{semantic\_score} \times W_{\text{sem}})$$
$$\text{final\_score} = \text{round}\Big(\min\big(1.0, \max(0.0, \text{base\_score} - \text{total\_penalty})\big), 4\Big)$$

- **Weight Validation**: `RankingConfig.validate()` enforces $W_{\text{kw}} \ge 0$, $W_{\text{sem}} \ge 0$, and $|(W_{\text{kw}} + W_{\text{sem}}) - 1.0| < 10^{-6}$.
- **Candidate Independence**: Individual scores and penalties are strictly invariant to the presence, absence, or ordering of other candidates.
- **Deterministic Tie-Breaking**: Batches sort primarily by `final_score` descending, secondarily by `resume.filename`, and tertiarily by `resume.candidate_name`.

### 2. Ranking Explanation (`ranking_reason`)
Generates comprehensive human-readable justifications:
> *"Matched 2/2 required skills (postgresql, python). Matched 1/1 preferred skills (docker). Strongest semantic alignment in experience (similarity: 0.63). Meets experience requirement (1.0/1.0 years). Final score: 0.6192 (Base: 0.6192 [KW: 1.0000 × 0.40 + Sem: 0.3653 × 0.60] - Penalty: 0.0000)"*

---

## 5. Calibration Methodology & Empirical Observations

To prevent presenting heuristics as statistics, we empirically measured the raw cosine similarity distributions of `all-MiniLM-L6-v2` across verified semantic pairs:

### 1. Empirical Measurements
- **Positive Semantic Pairs** (paraphrased backend requirements, relational databases, containers):
  - *"Develop and maintain backend APIs"* $\leftrightarrow$ *"Built HTTP services and web endpoints"*: raw = **0.5643**
  - *"Work with relational databases"* $\leftrightarrow$ *"Designed PostgreSQL schemas and optimized SQL"*: raw = **0.4874**
  - *"Containerize applications"* $\leftrightarrow$ *"Dockerized web microservices and set up CI/CD"*: raw = **0.5869**
  - *"Collaborate with agile engineering teams"* $\leftrightarrow$ *"Worked closely in 2-week sprints"*: raw = **0.5736**
  - **Positive Range**: **0.4874 to 0.5869** (mean: **0.5531**)
- **Negative Semantic Pairs** (unrelated roles, marketing, payroll, chef):
  - *"Python backend development"* $\leftrightarrow$ *"Graphic design and social media marketing"*: raw = **0.1413**
  - *"Build cloud infrastructure"* $\leftrightarrow$ *"Created promotional campaigns and brand graphics"*: raw = **0.1673**
  - *"Develop and maintain backend APIs"* $\leftrightarrow$ *"Chef de Partie preparing Mediterranean pastries"*: raw = **0.1494**
  - *"Design relational database schemas"* $\leftrightarrow$ *"Managed corporate payroll and travel"*: raw = **0.0993**
  - **Negative Range**: **0.0993 to 0.1673** (mean: **0.1393**)

### 2. Calibrated Value
- Updated `semantic_noise_threshold = 0.18`: cleanly zeroes out all negative pairs ($\le 0.1673$) while preserving positive dynamic range ($0.48 \text{ to } 0.85$).

---

## 6. 18-Candidate Evaluation Fixture Results

Evaluated against a Backend Software Engineer JD ($2.0$ yrs exp required; `python`, `postgresql`, `fastapi` required; `docker`, `aws` preferred):

| Rank | Candidate | Archetype | Final Score | Key Behavior Verified |
| :---: | :--- | :--- | :---: | :--- |
| **1** | `01 Excellent Backend` | All skills + 3 yrs exp | **0.7029** | Full skill coverage, high semantic depth, 0 penalty |
| **2** | `02 Fresher Strong Backend` | All skills + 0 yrs exp | **0.5902** | Strong skills & semantics; minor 0.10 gap penalty |
| **3** | `05 Full Stack` | React + Python backend | **0.5583** | Core backend skills satisfied |
| **4** | `14 Student Projects` | Strong FastAPI projects | **0.5365** | Project evidence compensates for 0 yrs experience |
| **5** | `09 Data Engineer` | Python + PostgreSQL | **0.5186** | Solid data/DB alignment |
| **6** | `03 Stuffed Skills` | Skills list, no context | **0.5135** | Keyword matched but penalized by weak semantic depth |
| **7** | `04 Paraphrased Backend` | 0 keywords, HTTP APIs | **0.4616** | Strong semantic evidence without exact brand tokens |
| **8** | `07 QA Automation` | Python + testing | **0.4439** | Python and testing alignment |
| **9** | `11 Java Backend` | Java + Spring Boot | **0.4042** | Microservice experience, but missing required Python/FastAPI |
| **10** | `08 DevOps` | Docker + AWS | **0.3794** | Preferred skills matched, missing core programming |
| **11** | `12 Data Scientist` | Python + ML | **0.3707** | Python matched, but lacks web API context |
| **12** | `13 Cloud Engineer` | AWS + Docker | **0.3394** | Preferred skills matched |
| **13** | `15 Student Basic` | 0 yrs, Python keyword | **0.2923** | Basic skills, 0.10 experience gap penalty |
| **14** | `06 Frontend Heavy` | React + Tailwind | **0.2526** | Mismatched domain (frontend vs backend) |
| **15** | `10 Mobile Dev` | Swift iOS | **0.2017** | Mismatched domain (mobile vs backend) |
| **16** | `16 Generic Software` | Vague corporate buzzwords | **0.1856** | Zero explicit skills, weak semantic relevance |
| **17** | `17 Marketer` | SEO + social media | **0.0894** | Unrelated discipline, noise-floor zeroed |
| **18** | `18 Pastry Chef` | Pastries & bakery | **0.0000** | Completely unrelated domain, score 0.0000 |

### Key Ranking Properties Confirmed:
1. **Required skills beat buzzwords**: `05 Full Stack` ($0.5583$) ranks far above `16 Generic Software` ($0.1856$).
2. **Context beats keyword repetition**: `01 Excellent Backend` ($0.7029$) significantly beats `03 Stuffed Skills` ($0.5135$).
3. **Paraphrase recognition**: `04 Paraphrased Backend` achieves $0.4616$ purely through semantic alignment despite $0.0000$ keyword score.
4. **Fresher competitiveness**: `02 Fresher Strong Backend` ranks #2 ($0.5902$) despite a $0.10$ experience gap deduction.
5. **Irrelevant filtering**: Unrelated candidates (`Pastry Chef`, `Marketer`) score $\le 0.0894$.

---

## 7. Complete Test Suite & Verification Results

Executed full pytest suite:
```bash
python -m pytest -v tests
```

**Results: 99 passed in 17.35s (100% pass rate)**

```
tests/test_edge_cases.py (5 passed)
tests/test_false_positives.py (4 passed)
tests/test_hybrid_ranker.py (18 passed)
tests/test_jd_extractor.py (6 passed)
tests/test_keyword_matcher.py (22 passed)
tests/test_models_and_config.py (2 passed)
tests/test_penalty_calculator.py (8 passed)
tests/test_resume_extractor.py (3 passed)
tests/test_semantic_matcher.py (21 passed)
tests/test_skill_normalizer.py (5 passed)
tests/test_text_cleaner.py (5 passed)
```

---

## 8. Important Explicit Disclaimers

1. **Provisional Weights**: The default weights ($W_{\text{kw}} = 0.40$, $W_{\text{sem}} = 0.60$) and penalty parameters ($0.05$/yr, $0.20$ cap) are provisional engineering configurations.
2. **Calibration Scope**: Semantic noise calibration ($\tau = 0.18$) is based on the local `all-MiniLM-L6-v2` model embedding behavior on technical text pairs.
3. **Synthetic Fixture Note**: The 18-candidate evaluation fixture tests algorithmic invariants and relative ranking logic; it is not a substitute for large-scale empirical recruiting benchmark datasets.

---

## 9. Next Recommended Task

- **Phase 5 — Recruiter UI & End-to-End Application**:
  - Build Streamlit user interface (`app/ui/` or `app/main.py`).
  - Implement dual PDF upload for 1 JD and 15–18 resumes.
  - Render ranked candidate leaderboard with interactive score breakdowns (`keyword_score`, `semantic_score`, `penalties`, `final_score`).
  - Provide expandable evidence drawers displaying matched skills, text snippets, and `ranking_reason`.
  - Add configurable weight sliders allowing recruiters to adjust keyword vs. semantic emphasis dynamically.
