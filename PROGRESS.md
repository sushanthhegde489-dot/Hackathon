# Smart Shortlisting Engine - Progress & Status

## Phase 1: Data Model & Extraction Hardening (Complete)
- Distinguished required skills vs secondary skills vs certifications vs tools vs minimum experience in JobDescription.
- Explicit negative constraint handling: excluded technologies, disallowed overlap, and anti-pattern penalties.
- Extraction rules: section header parsing, regex patterns, and normalized alias matching.

## Phase 2: Keyword Matching Engine (Complete)
- Clean, testable KeywordMatcher returning detailed match metrics.
- Direct impact on overall scoring (weights configurable via RankingConfig).

## Phase 3: Semantic Matching Engine (Complete)
- SentenceTransformer embeddings (all-MiniLM-L6-v2) running efficiently on CPU.
- Cosine similarity between JD requirements/context and candidate profile sections.

## Phase 4: Hybrid Ranker & Calibration (Complete)
- Calibrated default weights: 40% Keyword, 60% Semantic.
- Experience penalty formula with progressive gap scaling.
- Defensible tie-breaking and rank justifications.

## Phase 5: Ranking Audit, Calibration, & Adversarial Stress-Testing (Complete)
- 139 automated tests covering edge cases, adversarial resumes, negative constraint violations, and real corpus validations.
- Zero regression tolerance.

## Phase 6: Frontend / UI / UX Overhaul (Complete)
- Zero-Emoji Enforcement across entire application and UI components.
- Warm Neutral Design System (cream, ivory, beige, charcoal, selective red and green).
- Configuration Presets UX (clean titles, weight breakdown, no-emoji warnings).
- Candidate Spotlight (#1, #2, #3 badges, requirement table, clean chips).
- Full Ranked Leaderboard (dark warm brown header, alternating neutral beige body rows).
- Recruiter Q&A Engine (4 targeted questions, instant click-to-answer execution).
- Bonus Features styling (star prefix, single-line descriptions).
- 139/139 automated tests passing.

## Phase 7: Dark Mode & Palette Enhancement (Complete)
- **Dark Mode Support**: Added instant theme toggle in the sidebar (`Dark Mode` vs `Light Mode`), defaulting to Dark Mode.
- **Deep Palette Harmonization**:
  - Darker Greys: `#111418` (app background), `#191D24` (surfaces), `#1F242D` (cards), `#161B22` (light mode text).
  - Rich Espresso Brown: `#7A5B45` & `#3A2B20` in dark mode, `#543E2E` & `#38281D` in light mode for table headers, borders, bonus banners, and spotlight badges.
  - Light Blue Mixed Shades: `#60A5FA` / `rgba(96, 165, 250, 0.12)` in dark mode, `#2563EB` / `#EFF6FF` in light mode for system badges, preferred skill chips, active tabs, and Q&A suggestion headers.
- **Strict Constraint Adherence**: Zero non-UI changes; core algorithms, ranking models, and math untouched.
- **Testing**: 140/140 automated tests passing with 100% pass rate.
