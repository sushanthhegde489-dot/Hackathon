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

## Phase 8: Recruiter UX Refinements & Walnut Palette (Complete)
- **Preset Selection Guard**: Replaced selectbox with `st.sidebar.radio` so recruiters cannot delete, backspace, or type arbitrary prompt text into pre-calibrated profiles.
- **Branded Consistent Header**: Styled `.app-header` as a cohesive container with walnut brown border-left accent, charcoal surface, and soft sky blue gradient sheen.
- **Walnut Brown, Charcoal & Soft Sky Blue Gradients**:
  - Walnut Brown: `#5C4033`, `#6A4B35`, `#3F2B1E`, `#8E6548`.
  - Charcoal: `#14171B`, `#1C2026`, `#222730`, `#2E3540`.
  - Soft Sky Blue Gradients: `#70B5F9`, `rgba(112, 181, 249, 0.22)`, `--sky-gradient`.
- **Text Visibility & Contrast**: 100% explicit high-contrast foreground guarantees across markdown, tables, expanders, captions, inputs, and cards for both themes.
- **Leaderboard CSV Results Table**: Added dedicated "Leaderboard CSV Results Table" view tab with interactive, searchable, sortable dataframe displaying all CSV scoring columns directly on screen.
- **Multi-Step Processing Transparency**: Replaced minimal spinner with `st.status` 4-step progress execution and clear step banners, ensuring the UI never displays a blank empty state.
- **Recruiter Q&A Cleanup**: Removed suggested questions buttons from the UI, retaining the clean text inquiry input and submit button.
- **Testing**: 140/140 automated tests passing with 100% pass rate.

## Phase 9: Unified High-Contrast Theme & Clean Table (Complete)
- **Removed Dark Mode**: Eliminated dark mode toggle and streamlined to a single unified, professional light theme.
- **Maximum Background Text Contrast**: Deep dark charcoal typography (`#111827`, `#161B22`, `#374151`) on warm ivory cream (`#F8F6F2`) and white surfaces (`#FFFFFF`) for 100% legible, high-contrast reading.
- **Removed Stylized Leaderboard**: Replaced the custom HTML table with a clean, native, high-contrast interactive `st.dataframe` Leaderboard Results Table with all scoring, skill, and penalty columns, accompanied by instant CSV/JSON exports.
- **Zero Backend Changes**: All ranking, matching, scoring, and models strictly preserved.
- **Testing**: 140/140 automated tests passing with 100% pass rate.
