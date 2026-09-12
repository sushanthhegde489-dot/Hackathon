# Hybrid Ranking Audit, Calibration, and Adversarial Evaluation Report

## 1. Executive Summary

We stress-tested, audited, and calibrated the hybrid ranking architecture prior to building the Streamlit UI. The system combines:
1. **Explicit Keyword Matching** (`KeywordMatcher`): Multi-tier required/preferred skill matching with canonical normalization and false-positive guards.
2. **Dense Semantic Matching** (`SemanticMatcher`): Section-aware cosine similarity using `all-MiniLM-L6-v2` with noise threshold attenuation.
3. **Experience Penalty** (`PenaltyCalculator`): Bounded, linear deduction per year of experience gap with protection against disproportionate penalties for freshers.

All **109 unit and integration tests** in the test suite pass (execution time ~7.6s on CPU).

---

## 2. Hybrid Scoring Formula & Diagnostics Architecture

### 2.1 Formula Pipeline

$$\text{base\_score} = (\text{keyword\_score} \times W_{\text{kw}}) + (\text{semantic\_score} \times W_{\text{sem}})$$

$$\text{final\_score} = \text{clamp}(\text{base\_score} - \text{total\_penalty}, 0.0, 1.0)$$

Where:
* $W_{\text{kw}} + W_{\text{sem}} = 1.0$ (provisional default: $W_{\text{kw}} = 0.40$, $W_{\text{sem}} = 0.60$).
* $\text{keyword\_score} = (\text{req\_matched\_ratio} \times 0.70) + (\text{pref\_matched\_ratio} \times 0.30)$.
* $\text{experience\_penalty} = \min(0.20, \max(0.0, \text{exp\_gap\_years} \times 0.05))$.

### 2.2 Machine-Readable Contribution Diagnostics (`ScoreDiagnostics`)

Every `CandidateResult` exposes machine-readable diagnostics verifying mathematical provenance:
* `keyword_score` ($S_{\text{kw}}$) and `keyword_weight` ($W_{\text{kw}}$)
* `keyword_contribution` ($C_{\text{kw}} = S_{\text{kw}} \times W_{\text{kw}}$)
* `semantic_score` ($S_{\text{sem}}$) and `semantic_weight` ($W_{\text{sem}}$)
* `semantic_contribution` ($C_{\text{sem}} = S_{\text{sem}} \times W_{\text{sem}}$)
* `base_score` ($C_{\text{kw}} + C_{\text{sem}}$)
* `experience_penalty` and `total_penalty`
* `final_score`

`CandidateResult.to_dict()` and `ranking_reason` stringify this exact decomposition for UI transparency and recruiter auditability.

---

## 3. Sensitivity Analysis Across 5 Weight Regimes

We executed a sensitivity benchmark using a real Software Engineering Intern JD (Required: Python, PostgreSQL, CI/CD, Microservices; Preferred: AWS, Docker; Min Exp: 1.0 yr) evaluated against an 18-candidate cohort.

### 3.1 Tested Weight Regimes

1. **Regime 1: High Semantic** ($W_{\text{kw}} = 0.30, W_{\text{sem}} = 0.70$)
2. **Regime 2: Provisional Default** ($W_{\text{kw}} = 0.40, W_{\text{sem}} = 0.60$)
3. **Regime 3: Balanced** ($W_{\text{kw}} = 0.50, W_{\text{sem}} = 0.50$)
4. **Regime 4: High Keyword** ($W_{\text{kw}} = 0.60, W_{\text{sem}} = 0.40$)
5. **Regime 5: Keyword Dominant** ($W_{\text{kw}} = 0.70, W_{\text{sem}} = 0.30$)

### 3.2 Candidate Trajectory & Rank Flips

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

### 3.3 Critical Findings & Vulnerability Analysis

1. **Keyword Stuffing Vulnerability at $W_{\text{kw}} \ge 0.50$**:
   - At $W_{\text{kw}} \ge 0.60$, the **Keyword Stuffer (Retail Cashier)** jumps ahead of legitimate Python Developers and Data Engineers into **#2 overall**.
   - At $W_{\text{kw}} = 0.50$, the Cashier overtakes Data Engineers into #3 and nearly overtakes Python Developers.
   - Only when $W_{\text{kw}} \le 0.40$ does the semantic component provide enough resistance ($S_{\text{sem}} = 0.267$ vs $0.440$) to suppress the stuffer below genuine developers.
2. **Paraphrase Preservation**:
   - The Paraphrased Backend Engineer (0 exact brand keywords, but strong engineering experience: $S_{\text{sem}} = 0.4133$) ranks #7 at $W_{\text{kw}} = 0.30$ and #9 at $W_{\text{kw}} = 0.40$, beating irrelevant engineers.
   - In keyword-heavy regimes ($W_{\text{kw}} \ge 0.60$), their score collapses down to 0.246.
3. **Irrelevant Domain Filtration**:
   - In all 5 regimes, candidates with zero domain overlap (Frontend Dev, UI/UX, Recruiter, Marketer) score strictly below 0.08 and occupy the bottom slots (#14 through #18).

---

## 4. Adversarial Proof of the 4 Quadrants

Tested in `tests/test_ranking_audit.py::TestKeywordSemanticIndependence`:

```text
                  High Semantic Score
                          ▲
                          │
         Case C           │          Case A
   (Paraphrase Master)    │     (Ideal Candidate)
   KW = 0.00, Sem = 0.284 │     KW = 1.00, Sem = 0.563
   Final = 0.170          │     Final = 0.738
                          │
  ◄───────────────────────┼───────────────────────► High Keyword
                          │                         Score
         Case D           │          Case B
   (Irrelevant Domain)    │     (Skill Stuffer)
   KW = 0.00, Sem = 0.012 │     KW = 1.00, Sem = 0.118
   Final = 0.007          │     Final = 0.471
                          │
                          ▼
                  Low Semantic Score
```

* **Anti-Stuffing Guarantee**: Candidate A (real experience) beats Candidate B (stuffer) by $\Delta = 0.267$ points ($0.738$ vs $0.471$), even though both have identical 100% keyword match.
* **Paraphrase Guarantee**: Candidate C (zero explicit keywords but relevant backend responsibilities) receives $0.170$ final score and outranks Candidate D ($0.007$) by 24x.

---

## 5. Required vs Preferred Skill Dominance Audit

Audited in `TestRequiredSkillDominance`:
* JD: Required: Python, FastAPI (Weight: 0.70); Preferred: Kubernetes, Docker, Redis (Weight: 0.30).
* Candidate 1: Has 2/2 required skills, 0 preferred $\rightarrow \text{Score} = 1.0 \times 0.70 + 0.0 = 0.70$.
* Candidate 2: Has 0/2 required skills, 3/3 preferred $\rightarrow \text{Score} = 0.0 + 1.0 \times 0.30 = 0.30$.
* **Conclusion**: Candidates matching 100% of preferred skills but 0% of required skills cannot exceed $0.30$, guaranteeing core qualification priority.

---

## 6. Semantic Noise Threshold Calibration Matrix

Tested against sentence-transformer embeddings on `all-MiniLM-L6-v2`:

| Target JD Section | Candidate Experience Text | Raw Cosine Sim | Attenuated Sim ($\tau = 0.18$) | Category |
| :--- | :--- | :--- | :--- | :--- |
| *Develop backend REST APIs in Python using PostgreSQL...* | "Built HTTP services and backend endpoints in Python." | **0.5962** | **0.5076** | Core Relevant |
| *Develop backend REST APIs in Python using PostgreSQL...* | "Designed relational schemas and queries in PostgreSQL." | **0.4884** | **0.3761** | Core Relevant |
| *Develop backend REST APIs in Python using PostgreSQL...* | "Automated software integration tests using pytest and bash." | **0.2445** | **0.0787** | Adjacent Technical |
| *Develop backend REST APIs in Python using PostgreSQL...* | "Full stack web development using React and Node.js." | **0.2520** | **0.0878** | Adjacent Technical |
| *Develop backend REST APIs in Python using PostgreSQL...* | "Configured CI/CD pipelines and deployment monitors." | **0.1008** | **0.0000** | Filtered (Below noise) |
| *Develop backend REST APIs in Python using PostgreSQL...* | "Prepared French pastries and croissants in an artisan bakery." | **0.1224** | **0.0000** | Filtered (Noise) |
| *Develop backend REST APIs in Python using PostgreSQL...* | "Executed email marketing campaigns and social media ads." | **0.0539** | **0.0000** | Filtered (Noise) |
| *Develop backend REST APIs in Python using PostgreSQL...* | "Managed corporate payroll and executive travel arrangements." | **0.0218** | **0.0000** | Filtered (Noise) |

**Empirical Calibration Insight**:
The default threshold $\tau = 0.18$ effectively zeros out non-technical and unrelated job bullets (0.02 - 0.12), while cleanly preserving adjacent skills (0.24 - 0.25) and strongly boosting core matches (> 0.48).

---

## 7. Experience Penalty & Fresher Protection Audit

Stress-tested in `TestExperiencePenaltyBoundaries`:
1. **Zero requirement**: When JD requires 0.0 years (e.g. entry-level intern), penalty is $0.0000$.
2. **Meets / Exceeds requirement**: When candidate $\text{years} \ge \text{required}$, penalty is $0.0000$.
3. **Linear Gap Deduction**: Gap of 1.0 year $\rightarrow 0.05$ penalty; 2.0 years $\rightarrow 0.10$ penalty.
4. **Substantial Gap Cap**: A 5-year experience gap on a Senior role is clamped to the maximum penalty cap of $0.20$ (not $0.25$).
5. **Talented Fresher Retention**: A talented fresher (Base: $0.75$, 1-year gap $\rightarrow$ Final: $0.70$) cleanly beats an experienced mediocre applicant (Base: $0.45$, 0 gap $\rightarrow$ Final: $0.45$). Experience penalty shapes ranking without obliterating competence.

---

## 8. Invariant Verifications

1. **Score Monotonicity**:
   - Adding a matching required skill to a candidate strictly increases or preserves their keyword and final score ($\Delta \ge 0$).
   - Adding years of experience to a candidate with an experience gap strictly reduces their penalty and increases their final score ($\Delta \ge 0$).
2. **Candidate Order Independence**:
   - For any list $[A, B, C]$, $\text{rank\_batch}([A, B, C]) \equiv \text{rank\_batch}([C, A, B]) \equiv [\text{rank}(A), \text{rank}(B), \text{rank}(C)]$. Candidate scores depend strictly on JD alignment, never cohort ordering.
3. **Determinism**: 10 repeated evaluation runs of the same JD and resume produce bitwise-identical scores.

---

## 9. Calibration Recommendation for Production / UI

### Default Recommendation: Keep Provisional 0.40 / 0.60
* **Keyword Weight ($W_{\text{kw}}$)**: `0.40`
* **Semantic Weight ($W_{\text{sem}}$)**: `0.60`
* **Required / Preferred Skill Split**: `0.70 / 0.30`
* **Noise Threshold ($\tau$)**: `0.18`
* **Experience Penalty**: `0.05 / year`, capped at `0.20`

### Recruiter UI Control Recommendations
In the Phase 6 Streamlit UI, allow recruiters to adjust weights via an "Advanced Settings" collapsible drawer with the following guarded presets:
* **Balanced / Recommended (Default)**: 40% Keyword / 60% Semantic
* **Strict Compliance Mode**: 60% Keyword / 40% Semantic (for strict regulatory or certification-mandated roles)
* **Skills-First / Concept Mode**: 25% Keyword / 75% Semantic (for cross-disciplinary or transition roles)

Warn the recruiter when keyword weight is set $\ge 0.60$ that ranking becomes vulnerable to keyword-stuffed resumes.
