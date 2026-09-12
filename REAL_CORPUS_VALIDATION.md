# Real Resume Corpus Validation & Performance Benchmark

This document records the empirical validation of the **Smart Shortlisting Engine** across the actual candidate resume corpus provided in the repository (`data/resumes/`).

---

## 1. Corpus Inventory & Format Breakdown

A complete scan of `data/resumes/` reveals a total of **221 files** across multiple formats:

| File Extension | File Count | Role in Hackathon Pipeline |
| :--- | :---: | :--- |
| **`.pdf`** | **54** | **Canonical Submission Format**: Primary ingestion format evaluated by the matching engine. |
| `.docx` | 122 | Alternate office export representation (excluded from PDF counts to prevent duplication). |
| `.txt` | 22 | Plaintext transcripts of selected resumes (used for unit fixture cross-checks). |
| `.xml` | 22 | Structured XML representations of selected resumes. |
| `.zip` | 1 | Archive container. |
| **Total** | **221** | |

### Ingestion Success Rate
- **Total PDFs Evaluated**: 54
- **Clean Ingestion & Text Extraction**: 54 (100.0%)
- **Corrupted / Empty Extraction**: 0 (0.0%)
- **Average Extraction Latency**: ~1.3 ms per resume.

---

## 2. Duplicate & Alternate Representation Handling

### Analysis
Multiple candidates possess multi-format exports (e.g. `App_Developer_Resume_1_Siddharth_Rao.pdf`, `.docx`, `.txt`, `.xml`). 
If unmanaged, counting duplicate formats would artificially inflate candidate pools and skew statistical distributions.

### Solution Implemented
1. **PDF Exclusivity**: The production ingestion pipeline strictly filters for `.pdf` files, treating PDF as the sole canonical submission medium per hackathon specifications.
2. **Deterministic Deduplication**: In `app/ui_helpers.py` (`validate_resume_batch`), filenames and candidate identifiers are deduplicated. When loading the curated 18-candidate batch, distinct candidates across disparate technical domains are chosen.
3. **Multi-Domain Coverage**: The selected 18-candidate benchmark comprises:
   - **Core Backend**: `python_dev__karan_verma.pdf`, `python_dev__sneha_reddy.pdf`
   - **Software Engineering**: `sde__arjun_desai.pdf`, `sde__ishaan_kapoor.pdf`
   - **Python Developers**: `Python_Developer_Resume_1_Karan_Malhotra.pdf`, `Python_Developer_Resume_2_Ananya_Reddy.pdf`
   - **Full Stack / Systems**: `SDE_Resume_1_Aditya_Joshi.pdf`, `SDE_Resume_2_Meera_Pillai.pdf`
   - **Adjacent Tech**: `ai_dev__rohan_mehta.pdf`, `data_scientist__nikhil_rao.pdf`, `web_dev__aditya_kulkarni.pdf`, `app_dev__rahul_bose.pdf`
   - **IT & Security**: `cyber_security__vikram_singh.pdf`, `it_support__deepak_yadav.pdf`
   - **Unrelated Control Baselines**: `founder_s_office__siddharth_rao.pdf`, `marketing__harsh_vardhan.pdf`, `sales__aman_tiwari.pdf`, `social_media_intern__sara_khan.pdf`

---

## 3. End-to-End Benchmark Execution

### Evaluation Setup
- **Job Description**: *Backend Software Engineer* (Sample JD)
  - **Required Skills**: Python, FastAPI, PostgreSQL, Microservices, CI/CD
  - **Preferred Skills**: Docker, Kubernetes, AWS, Redis
  - **Experience Required**: 2.0 Years
- **Batch Size**: Exactly 18 real PDF resumes.
- **Hardware**: Standard x86_64 CPU (Local Windows execution, 0 GPU required).
- **Model**: `all-MiniLM-L6-v2` loaded locally from `models/all-MiniLM-L6-v2`.

### Execution Timing
| Stage | Duration | Notes |
| :--- | :---: | :--- |
| **PDF Text Extraction (18 files)** | **0.024s** | In-memory stream extraction via `pypdf`. |
| **Structured Parsing & Normalization** | **0.015s** | Multi-tier skill extraction & section segmentation. |
| **Local Semantic Embedding & Hybrid Ranking** | **8.580s** | Batched CPU encoding (100% offline, zero API latency). |
| **Total Pipeline Latency** | **8.619s** | **~0.47s per candidate end-to-end**. |
| **Subsequent Weight Adjustments** | **< 0.010s** | Cached embeddings allow instantaneous slider updates. |

---

## 4. Benchmark Ranking Results

| Rank | Candidate Name | Filename | Final Score | Base Score | Keyword Score ($S_{\text{kw}}$) | Semantic Score ($S_{\text{sem}}$) | Experience | Penalty | Profile Summary |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **🥇 #1** | **Karan Verma** | `python_dev__karan_verma.pdf` | **53.7%** | 53.7% | 67.5% | 44.4% | 2.5 yrs | 0.0% | Deep Python & backend architecture; satisfies experience requirement. |
| **🥈 #2** | **Arjun Desai** | `sde__arjun_desai.pdf` | **48.3%** | 48.3% | 50.0% | 47.1% | 2.0 yrs | 0.0% | Highest semantic alignment across project sections; strong backend foundations. |
| **🥉 #3** | **Ananya Reddy** | `Python_Developer_Resume_2_Ananya_Reddy.pdf` | **36.0%** | 46.0% | 52.5% | 41.7% | 0.0 yrs | -10.0% | Strong technical skills; slight deduction for entry-level experience gap. |
| **#4** | Karan Malhotra | `Python_Developer_Resume_1_Karan_Malhotra.pdf` | **35.8%** | 45.8% | 52.5% | 41.3% | 0.0 yrs | -10.0% | Comparable skill match to #3; separated by 0.002 on semantic depth. |
| **#5** | Sneha Reddy | `python_dev__sneha_reddy.pdf` | **29.9%** | 39.9% | 40.7% | 39.3% | 0.0 yrs | -10.0% | Solid Python skills, partial preferred skill alignment. |
| **#6** | Ishaan Kapoor | `sde__ishaan_kapoor.pdf` | **26.9%** | 26.9% | 25.0% | 28.2% | 2.0 yrs | 0.0% | Generalist SDE profile; partial backend overlap. |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |
| **#16** | Siddharth Rao | `founder_s_office__siddharth_rao.pdf` | **0.0%** | 5.9% | 0.0% | 9.8% | 0.0 yrs | -10.0% | Unrelated operations & strategy background; correctly zeroed out. |
| **#17** | Harsh Vardhan | `marketing__harsh_vardhan.pdf` | **0.0%** | 6.4% | 0.0% | 10.7% | 0.0 yrs | -10.0% | Growth marketing profile; cleanly suppressed by noise threshold ($\tau=0.18$). |
| **#18** | Sara Khan | `social_media_intern__sara_khan.pdf` | **0.0%** | 3.8% | 0.0% | 6.3% | 0.0 yrs | -10.0% | Non-technical background; zero false positive accumulation. |

---

## 5. Audit & Evidence Quality Observations

1. **Clean Separation of Fit**:
   - Software and Python developers populate Ranks #1 through #6 with final scores ranging from 53.7% to 26.9%.
   - Non-technical baselines (Marketing, Sales, Social Media, Founder's Office) score $\le 6.4\%$ base score and are cleanly suppressed to **0.0% final score**.
2. **Semantic Attenuation ($\tau = 0.18$)**:
   - The calibrated noise floor effectively stops generic corporate resume text from accumulating artificial similarity.
3. **Experience Fairness**:
   - Qualified candidates with 0 formal years of experience (Ananya Reddy, Karan Malhotra) still secure top-4 ranks despite a calibrated 10% experience deduction, demonstrating that technical excellence can overcome modest experience gaps.
4. **Top-3 Explainability**:
   - Every top-3 candidate has fully populated skill evidence, strongest semantic quote references, and exact mathematical score provenance.
