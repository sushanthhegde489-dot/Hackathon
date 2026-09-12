# Resume & Job Description Ranking Engine

## Overview

The **Smart Candidate Shortlisting Engine** is a fully offline, privacy-first recruitment analytics tool that evaluates resumes against a target job description. It determines candidate suitability through explicit skill extraction, section-aware semantic similarity, and experience penalties, providing recruiters with an explainable and deterministic ranking.

## Problem

Recruiters and hiring managers often evaluate hundreds of resumes against a job description. Traditional keyword-matching approaches have critical flaws:
* **Brittle Matching**: They miss paraphrased experience or synonyms.
* **Keyword Stuffing**: They disproportionately reward unqualified candidates (e.g., a cashier copy-pasting a list of frameworks) over experienced engineers.
* **Lack of Context**: They fail to differentiate between a skill used in a professional project versus a skill mentioned in passing.
* **Black-Box AI**: Modern LLM-based solutions are often slow, expensive, hallucinate requirements, and offer poor mathematical provenance for why one candidate was ranked above another.

## Solution

This project solves these issues through a **Deterministic Hybrid Ranker** that combines:
* Canonical exact-match skill verification.
* Dense semantic similarity on local technical sections (Experience/Projects) using an offline embedding model.
* Bounded structured experience penalties.
* 100% transparent score provenance and evidence-backed Q&A.

## Key Features

* **100% Offline & Local**: Executes entirely on local CPU (`all-MiniLM-L6-v2`) with zero external API calls, ensuring absolute data privacy.
* **Requirement Evidence Table**: Maps every JD requirement to an explicit resume snippet.
* **Adversarial Safety**: Actively warns recruiters when keyword weights reach levels vulnerable to keyword stuffing.
* **Interactive Recruiter Q&A**: Answers comparative and exclusion queries (e.g., "Why is #1 above #2?", "Who has Docker?") instantly based strictly on structured evidence.
* **JD Bias Detection**: Audits job descriptions for pedigree bias, restrictive phrasing, and experience inflation without altering candidate scores.

## Architecture

The system pipeline operates in distinct stages:
1. **Ingestion**: In-memory PDF parsing and text token-preserving normalization.
2. **Extraction**: Regex and heuristic multi-tier extraction of contact info, skills, experience, and sections.
3. **Normalization**: Canonical mapping of skill aliases (e.g., `k8s` → `kubernetes`).
4. **Matching**: Independent execution of `KeywordMatcher`, `SemanticMatcher`, and `PenaltyCalculator`.
5. **Ranking**: Hybrid weighted combination generating a final score between `0.0` and `1.0`.
6. **Presentation**: Streamlit interactive dashboard with CSV/JSON export.

## Ranking Methodology

The ranking engine evaluates three independent components:
1. **Keyword Score**: Evaluates required and preferred skills independently, weighted (default 70% required / 30% preferred).
2. **Semantic Score**: Computes cosine similarity between JD technical sections and candidate Experience/Projects sections, gated by an empirical noise threshold.
3. **Experience Penalty**: Evaluates the gap between required experience and candidate experience.

## Scoring Formula

```text
Base Score = 
    Keyword Score × Keyword Weight 
    + 
    Semantic Score × Semantic Weight

Final Score = 
    clamp(Base Score − Experience Penalty, 0, 1)
```

By default, the engine applies a **40% Keyword Weight** and **60% Semantic Weight**.

## Explainability

Every candidate in the leaderboard features a deep-dive inspection drawer exposing:
* **Matched/Missing Requirements**: Which mandatory skills were satisfied.
* **Semantic Alignments**: The top textual similarities identified by the vector model.
* **Mathematical Decomposition**: The exact mathematical pipeline determining the final score.
* **Raw Extraction**: The raw text parsed from the PDF for manual verification.

## Semantic Matching

Semantic matching leverages the `all-MiniLM-L6-v2` Sentence Transformer. Instead of comparing entire documents indiscriminately, the engine matches specific JD requirements against candidate Experience and Project sections. This prevents candidates from achieving high semantic scores merely by dumping technical jargon into an "Interests" section.

## Experience Penalty

Candidates lacking required experience are not immediately disqualified. Instead, a bounded linear penalty is applied:
* **Gap Calculation**: `max(0, required_years - candidate_years)`
* **Deduction**: 0.05 points per year of missing experience.
* **Maximum Cap**: Penalty is capped at 0.20 to ensure highly skilled junior engineers remain visible for exceptional technical alignments.

## Adversarial / Calibration Testing

The engine's configuration is derived from empirical calibration across a robust baseline of diverse resumes. We discovered that setting the Keyword Weight $\ge 0.60$ allows keyword-stuffed resumes to outperform legitimate experienced professionals. Consequently, the default configuration prioritizes semantic contextual matching over strict keyword repetition.

## Dataset / Demo Data

The repository includes a curated corpus of 54 real PDF resumes located in `data/resumes/`. The application provides a one-click demo loader to immediately evaluate 18 representative candidates against a sample Backend Engineer job description.

## Project Structure

```text
app/
├── main.py                     # Streamlit application entrypoint
├── config.py                   # Default parameters and models
├── models.py                   # Core dataclasses and schemas
├── ui_helpers.py               # Streamlit styling and formatters
├── bias/
│   └── jd_bias_detector.py     # Bias & inclusivity pre-screener
├── matching/
│   ├── hybrid_ranker.py        # Final score combination logic
│   ├── keyword_matcher.py      # Canonical skill evaluation
│   ├── penalty_calculator.py   # Experience gap computation
│   └── semantic_matcher.py     # Section-aware similarity scoring
└── qa/
    └── recruiter_qa.py         # Evidence-backed Q&A engine

extraction/
├── jd_extractor.py             # Parses job description schemas
├── resume_extractor.py         # Parses resume sections and skills
└── skill_normalizer.py         # Resolves technological aliases

ingestion/
├── pdf_parser.py               # Handles disk and byte-stream PDFs
└── text_cleaner.py             # Normalizes text spacing and punctuation

tests/                          # 134 unit and integration tests
data/                           # Demo resumes and sample JDs
models/                         # Local offline embedding model weights
```

## Installation

```powershell
# 1. Clone the repository
git clone https://github.com/your-org/Hackathon.git
cd Hackathon

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate  # On Linux/macOS use: source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Running the Application

```powershell
streamlit run app/main.py
```

Navigate to `http://localhost:8501` in your browser.

## Running Tests

```powershell
python -m pytest -v tests
```

## Example Workflow

1. Start the Streamlit application.
2. Under **Step 1: Job Description**, select "Backend Engineer (Sample)" and click **Load Selected Sample JD**.
3. Under **Step 2: Batch Resume Processing**, click **⚡ Load 18 Demo Resumes**.
4. Click **🚀 Rank Resumes Against Job Description**.
5. Observe the Top 3 Spotlight Cards, expanding the requirement evidence tables.
6. Interact with the **Recruiter Q&A Assistant** by asking "Why did #1 rank above #2?"
7. Open a candidate's inspection drawer to review their exact mathematical score decomposition.

## Configuration

Default scoring parameters can be adjusted directly in the UI sidebar, or globally within `app/config.py`:
* `keyword_weight`: 0.40
* `semantic_weight`: 0.60
* `required_skill_weight`: 0.70
* `preferred_skill_weight`: 0.30
* `semantic_noise_threshold`: 0.18
* `experience_penalty_per_year`: 0.05
* `maximum_experience_penalty`: 0.20

## Limitations

* **OCR Missing**: The `pypdf` ingestion pipeline cannot read flattened image-based PDFs without an embedded text layer.
* **Experience Parsing**: Extraction of experience years relies on regex heuristics and may occasionally misinterpret overlapping date ranges.
* **Semantic Constraints**: The `all-MiniLM-L6-v2` model is highly optimized for CPU but lacks the deep reasoning capabilities of larger parameter models. 

## Future Improvements

* Integrate a local Tesseract OCR fallback for scanned PDFs.
* Extend the canonical skill graph dynamically using a localized lightweight taxonomy.
* Replace the linear penalty model with a curve based on historical hiring outcomes.

## Technology Stack

* **Python 3.10+**
* **Streamlit** (UI / Frontend)
* **Sentence-Transformers & PyTorch** (Offline Embeddings)
* **NumPy** (Cosine Similarity via Dot Product on Normalized Vectors)
* **pypdf** (PDF Ingestion)
* **pytest** (Testing)
