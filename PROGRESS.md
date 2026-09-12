# Project Progress & Architectural Status

## 1. Current Architectural Status

The end-to-end backend pipeline — PDF ingestion, text normalization, multi-tier JD/resume extraction, canonical keyword matching, section-aware semantic matching, experience penalty calculation, machine-readable score diagnostics, and hybrid ranking — is **fully implemented, calibrated, audited, and verified**.
All **109 unit, integration, and benchmark tests** are passing (100% pass rate in ~7.6s on CPU).

---

## 2. Phase 5 — Ranking Audit, Calibration, and Adversarial Evaluation

### Files Created / Changed
- [`app/models.py`](file:///c:/Users/Sushanth/Downloads/Hackathon/app/models.py): Added `ScoreDiagnostics` dataclass and integrated `diagnostics` field and `base_score` property into `CandidateResult` and `CandidateResult.to_dict()`.
- [`app/matching/hybrid_ranker.py`](file:///c:/Users/Sushanth/Downloads/Hackathon/app/matching/hybrid_ranker.py): Updated `rank()` and `rank_batch()` to compute, validate, and attach `ScoreDiagnostics` to each `CandidateResult`.
- [`app/matching/semantic_matcher.py`](file:///c:/Users/Sushanth/Downloads/Hackathon/app/matching/semantic_matcher.py): Added `get_embedding_model()` classmethod for shared model reuse and analysis.
- [`app/config.py`](file:///c:/Users/Sushanth/Downloads/Hackathon/app/config.py): Pointed `DEFAULT_EMBEDDING_MODEL` to local model directory `models/all-MiniLM-L6-v2` for zero-latency, 100% offline CPU execution.
- [`tests/test_ranking_audit.py`](file:///c:/Users/Sushanth/Downloads/Hackathon/tests/test_ranking_audit.py) *(NEW)*: 10 adversarial, diagnostic, noise distribution, monotonicity, and candidate-order independence tests.
- [`RANKING_CALIBRATION.md`](file:///c:/Users/Sushanth/Downloads/Hackathon/RANKING_CALIBRATION.md) *(NEW)*: Comprehensive audit and calibration report documenting sensitivity curves, rank flips, adversarial quadrants, and UI control recommendations.

---

## 3. Machine-Readable Score Diagnostics (`ScoreDiagnostics`)

Every candidate result now surfaces full mathematical provenance:
* `keyword_score` ($S_{\text{kw}}$) and `keyword_weight` ($W_{\text{kw}}$)
* `keyword_contribution` ($C_{\text{kw}} = S_{\text{kw}} \times W_{\text{kw}}$)
* `semantic_score` ($S_{\text{sem}}$) and `semantic_weight` ($W_{\text{sem}}$)
* `semantic_contribution` ($C_{\text{sem}} = S_{\text{sem}} \times W_{\text{sem}}$)
* `base_score` ($C_{\text{kw}} + C_{\text{sem}}$)
* `experience_penalty` and `total_penalty`
* `final_score`

`to_dict()` and `ranking_reason` render these exact decomposed terms for UI transparency.

---

## 4. Sensitivity Analysis Across 5 Weight Regimes

Tested on an 18-candidate benchmark against a Software Engineering Intern JD (Required: Python, PostgreSQL, CI/CD, Microservices; Preferred: AWS, Docker; Exp Req: 1.0 yr):

| Candidate Archetype | Resume Profile Summary | KW=0.3 / SEM=0.7 | KW=0.4 / SEM=0.6 | KW=0.5 / SEM=0.5 | KW=0.6 / SEM=0.4 | KW=0.7 / SEM=0.3 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Backend Engineer** | 4/4 req + 2/2 pref, deep FastAPI experience | **#1** (0.694) | **#1** (0.738) | **#1** (0.781) | **#1** (0.825) | **#1** (0.869) |
| **Python Developer** | 2/4 req + 1/2 pref, real Django backend exp | **#2** (0.458) | **#2** (0.464) | **#2** (0.470) | **#3** (0.476) | **#3** (0.482) |
| **Data Engineer Intern** | 2/4 req + 1/2 pref, real SQL/PostgreSQL exp | **#3** (0.437) | **#3** (0.446) | **#4** (0.455) | **#4** (0.464) | **#4** (0.473) |
| **Keyword Stuffer (Cashier)** | List of tech skills, supermarket cashier exp | **#4** (0.382) | **#4** (0.420) | **#3** (0.458) | **#2** (0.497) ⚠️ | **#2** (0.535) ⚠️ |
| **DevOps Intern** | 0/4 req + 2/2 pref (Docker/AWS/K8s) | **#5** (0.360) | **#5** (0.377) | **#5** (0.393) | **#5** (0.410) | **#5** (0.426) |
| **Full Stack Developer** | 2/4 req + 0/2 pref (React + Python) | **#6** (0.355) | **#7** (0.354) | **#7** (0.353) | **#7** (0.353) | **#7** (0.352) |
| **Backend Paraphrase** | 0 brand keywords, deep server & API exp | **#7** (0.342) | **#9** (0.318) | **#10** (0.294) | **#10** (0.270) | **#10** (0.246) |
| **QA Automation** | 1/4 req (pytest/CI/CD), API test exp | **#9** (0.324) | **#8** (0.327) | **#8** (0.331) | **#8** (0.335) | **#8** (0.339) |
| **Backend Fresher (0 yr)** | 2/4 req, academic coursework, 0 yr exp | **#10** (0.295) | **#10** (0.295) | **#9** (0.296) | **#9** (0.297) | **#9** (0.298) |
| **Frontend Dev 1** | React/Tailwind/JS, zero backend | **#14** (0.074) | **#14** (0.064) | **#14** (0.053) | **#14** (0.042) | **#14** (0.032) |
| **Digital Marketer** | Google Ads, SEO, social media | **#18** (0.006) | **#18** (0.006) | **#18** (0.005) | **#18** (0.004) | **#18** (0.003) |

### Key Takeaway:
At $W_{\text{kw}} \ge 0.60$, the **Keyword Stuffer (Retail Cashier)** flips ranks to jump into **#2 overall**, beating legitimate developers. At $W_{\text{kw}} \le 0.40$, the semantic component successfully resists stuffing, keeping the Cashier at #4 and preserving legitimate engineers at the top.

---

## 5. Adversarial 4-Quadrant Verification

Verified in `TestKeywordSemanticIndependence`:
* **Case A (High KW 1.0, High Sem 0.56)**: Final = $0.738$ (Top tier).
* **Case B (High KW 1.0, Low Sem 0.12 - Stuffer)**: Final = $0.471$ (Defeated by Case A by $\Delta = 0.267$).
* **Case C (Zero KW 0.0, Strong Sem 0.28 - Paraphrase)**: Final = $0.170$ (Receives meaningful credit without brand keywords).
* **Case D (Zero KW 0.0, Low Sem 0.01 - Irrelevant)**: Final = $0.007$ (Effectively zeroed out; Case C is 24x higher).

---

## 6. Complete Test Suite & Verification Results

Executed full pytest suite:
```bash
python -m pytest -v tests
```

**Results: 109 passed in 7.63s (100% pass rate)**

```
tests/test_edge_cases.py (5 passed)
tests/test_false_positives.py (4 passed)
tests/test_hybrid_ranker.py (18 passed)
tests/test_jd_extractor.py (6 passed)
tests/test_keyword_matcher.py (22 passed)
tests/test_models_and_config.py (2 passed)
tests/test_penalty_calculator.py (8 passed)
tests/test_ranking_audit.py (10 passed)  <-- NEW PHASE 5 SUITE
tests/test_resume_extractor.py (3 passed)
tests/test_semantic_matcher.py (21 passed)
tests/test_skill_normalizer.py (5 passed)
tests/test_text_cleaner.py (5 passed)
```

---

## 7. Calibration Recommendation

* **Retain provisional default**: Keyword Weight = `0.40`, Semantic Weight = `0.60`.
* **Skill Split**: Required = `0.70`, Preferred = `0.30`.
* **Noise Threshold**: $\tau = 0.18$ (attenuates non-technical text while preserving domain matches).
* **Experience Penalty**: $0.05$/yr gap, clamped at $0.20$ maximum.
* **UI Controls**: Expose presets (Default 40/60, Strict Compliance 60/40, Skills-First 25/75) with visual warnings when keyword weight $\ge 0.60$.

---

## 8. Next Recommended Task

- **Phase 6 — Streamlit Recruiter Application**:
  - Build interactive UI in `app/ui/` or `app/main.py`.
  - Implement dual file upload: 1 Job Description PDF + 15–18 Resume PDFs.
  - Interactive ranked leaderboard with live score diagnostics (`keyword_contribution`, `semantic_contribution`, `penalty`, `final_score`).
  - Evidence drawers showing exact matched skills, sentence similarity evidence, and human-readable `ranking_reason`.
  - Advanced configuration drawer with preset selector and sensitivity warning.
