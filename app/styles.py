"""
app/styles.py - High-Contrast Professional Theme.
Palette:
- Background: Warm ivory cream (#F8F6F2) and crisp white surfaces (#FFFFFF).
- Typography: Deep dark charcoal (#111827 / #161B22) for maximum readability and contrast.
- Walnut Brown: #5C4033, #3B281B, #7A5643 (rich earthy walnut accents).
- Soft Sky Blue Gradients: #2563EB, #1D70B8, with subtle soft sky blue gradient accents.
- Selective Red (#A8201A) & Selective Green (#1E6B37).
Strictly zero emojis. Professional recruiter SaaS aesthetic.
"""

def get_app_css() -> str:
    """Returns the single unified, high-contrast stylesheet."""
    return """
<style>
/* -------------------------------------------------------------------------
   1. GLOBAL RESETS & HIGH-CONTRAST PALETTE VARIABLES
------------------------------------------------------------------------- */
:root {
    /* Surfaces */
    --bg-main: #F8F6F2;
    --bg-surface: #FFFFFF;
    --bg-secondary: #EFECE6;
    --bg-card: #FFFFFF;
    --bg-card-hover: rgba(37, 99, 235, 0.04);

    /* Borders: walnut brown and neutral slate */
    --border-subtle: #D8D2C7;
    --border-medium: #BFB6A8;
    --border-brown: #5C4033;
    --border-blue: #BED6F2;

    /* High-contrast dark charcoal typography */
    --text-primary: #111827;
    --text-secondary: #374151;
    --text-muted: #6B7280;

    /* Walnut Brown tones */
    --walnut-brown: #5C4033;
    --walnut-brown-dark: #3B281B;
    --walnut-brown-light: #7A5643;
    --walnut-brown-bg: #F7F1EB;
    --walnut-brown-border: #DBCBBF;

    /* Charcoal tones */
    --charcoal-dark: #111827;
    --charcoal-surface: #1F2937;
    --charcoal-card: #FFFFFF;

    /* Compatibility aliases */
    --brand-brown: var(--walnut-brown);
    --brand-brown-dark: var(--walnut-brown-dark);
    --brand-brown-light: var(--walnut-brown-light);
    --brand-dark: #1F2937;
    --brand-darker: #111827;

    /* Soft Sky Blue & Gradients */
    --sky-blue: #1D70B8;
    --sky-blue-hover: #155894;
    --sky-blue-bg: #EFF6FF;
    --sky-blue-border: #BFDBFE;
    --accent-blue: var(--sky-blue);
    --accent-blue-bg: var(--sky-blue-bg);
    --accent-blue-border: var(--sky-blue-border);

    /* Gradients */
    --header-bg-gradient: linear-gradient(135deg, rgba(247, 241, 235, 0.95) 0%, #FFFFFF 55%, rgba(239, 246, 255, 0.85) 100%);
    --sky-gradient: linear-gradient(135deg, rgba(29, 112, 184, 0.12) 0%, rgba(92, 64, 51, 0.08) 100%);

    /* Selective red & green */
    --accent-red: #A8201A;
    --accent-red-hover: #8C1A15;
    --accent-red-bg: #FCEBEB;
    --accent-red-border: #F7C5C5;

    --success-green: #1E6B37;
    --success-green-bg: #EBF5EE;
    --success-green-border: #C6E7CE;

    /* Shadows & inputs */
    --card-shadow: 0 1px 3px rgba(17, 24, 39, 0.06);
    --card-hover-shadow: 0 4px 12px rgba(17, 24, 39, 0.10);
    --input-bg: #FFFFFF;
    --input-border: #BFB6A8;
}

/* Page background and high-contrast typography */
.stApp {
    background-color: var(--bg-main) !important;
    color: var(--text-primary) !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

/* Main container layout */
.main .block-container {
    max-width: 1200px;
    padding-top: 1.5rem;
    padding-bottom: 4rem;
    padding-left: 2rem;
    padding-right: 2rem;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background-color: var(--bg-secondary) !important;
    border-right: 1px solid var(--border-subtle) !important;
}

[data-testid="stSidebar"] hr {
    border-color: var(--border-subtle) !important;
}

/* High-contrast typography guarantees */
h1, h2, h3, h4, h5, h6 {
    color: var(--text-primary) !important;
    letter-spacing: -0.015em;
    font-weight: 700;
}

p, span, label, div {
    color: var(--text-primary);
}

.stCaption, small {
    color: var(--text-secondary) !important;
    font-weight: 500;
}

/* Buttons */
.stButton > button {
    background-color: var(--bg-surface) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-medium) !important;
    border-radius: 6px;
    font-weight: 600;
    font-size: 0.88rem;
    padding: 0.45rem 1rem;
    transition: all 0.15s ease;
    box-shadow: var(--card-shadow);
}

.stButton > button:hover {
    background-color: var(--bg-card-hover) !important;
    border-color: var(--sky-blue) !important;
    color: var(--sky-blue) !important;
}

/* Primary buttons */
.stButton > button[kind="primary"] {
    background-color: var(--accent-red) !important;
    color: #FFFFFF !important;
    border: 1px solid var(--accent-red) !important;
    font-weight: 700;
}

.stButton > button[kind="primary"]:hover {
    background-color: var(--accent-red-hover) !important;
    border-color: var(--accent-red-hover) !important;
    color: #FFFFFF !important;
}

/* Download buttons */
.stDownloadButton > button {
    background-color: var(--bg-surface) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-medium) !important;
    border-radius: 6px;
    font-weight: 600;
    font-size: 0.84rem;
    padding: 0.45rem 0.9rem;
}

.stDownloadButton > button:hover {
    background-color: var(--bg-card-hover) !important;
    border-color: var(--sky-blue) !important;
    color: var(--sky-blue) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background-color: transparent !important;
    border-bottom: 2px solid var(--border-subtle) !important;
    gap: 1.5rem;
}

.stTabs [data-baseweb="tab"] {
    color: var(--text-secondary) !important;
    font-weight: 600;
    font-size: 0.92rem;
    padding: 0.5rem 0.25rem;
    border-bottom: 2px solid transparent;
}

.stTabs [data-baseweb="tab"][aria-selected="true"] {
    color: var(--sky-blue) !important;
    font-weight: 700;
    border-bottom: 2px solid var(--sky-blue) !important;
}

/* Expanders */
.streamlit-expanderHeader {
    background-color: var(--bg-surface) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: 6px;
    color: var(--text-primary) !important;
    font-weight: 600;
    font-size: 0.9rem;
}

.streamlit-expanderHeader:hover {
    border-color: var(--border-medium) !important;
    color: var(--sky-blue) !important;
}

[data-testid="stExpander"] {
    border: none;
    margin-bottom: 0.75rem;
}

[data-testid="stExpander"] details summary span {
    color: var(--text-primary) !important;
    font-weight: 600;
}

/* Inputs, text areas, and selectboxes */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > div {
    background-color: var(--input-bg) !important;
    border: 1px solid var(--input-border) !important;
    border-radius: 6px !important;
    color: var(--text-primary) !important;
    font-size: 0.92rem !important;
    font-weight: 500;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--sky-blue) !important;
    box-shadow: 0 0 0 1px var(--sky-blue) !important;
}

/* Radio button text */
[data-testid="stRadio"] label {
    color: var(--text-primary) !important;
    font-weight: 600;
}

/* Sliders */
div[data-baseweb="slider"] [role="slider"] {
    background-color: var(--sky-blue) !important;
    border-color: var(--sky-blue) !important;
}

/* Status widget */
[data-testid="stStatusWidget"] {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border-subtle) !important;
    border-left: 4px solid var(--sky-blue) !important;
    border-radius: 6px;
}

/* Interactive DataFrame */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border-subtle) !important;
    border-radius: 6px;
    background-color: var(--bg-surface) !important;
}

/* Custom Alert / Callout Boxes */
.custom-alert {
    padding: 0.75rem 1rem;
    border-radius: 6px;
    font-size: 0.88rem;
    line-height: 1.45;
    margin: 0.6rem 0;
}

.custom-alert-success {
    background-color: var(--success-green-bg);
    border: 1px solid var(--success-green-border);
    color: var(--success-green);
    font-weight: 600;
}

.custom-alert-warning {
    background-color: var(--accent-red-bg);
    border: 1px solid var(--accent-red-border);
    color: var(--accent-red);
    font-weight: 600;
}

.custom-alert-info {
    background-color: var(--sky-blue-bg);
    border: 1px solid var(--sky-blue-border);
    color: var(--text-primary);
    font-weight: 600;
}

/* -------------------------------------------------------------------------
   2. HEADER & BRANDING
------------------------------------------------------------------------- */
.app-header {
    background: var(--header-bg-gradient);
    border: 1px solid var(--border-subtle);
    border-left: 4px solid var(--walnut-brown);
    border-radius: 8px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.75rem;
    box-shadow: var(--card-shadow);
}

.app-title {
    font-size: 1.95rem;
    font-weight: 700;
    color: var(--text-primary) !important;
    margin: 0 0 0.35rem 0;
    letter-spacing: -0.02em;
}

.app-subtitle {
    font-size: 0.94rem;
    color: var(--text-secondary) !important;
    margin: 0 0 0.85rem 0;
    line-height: 1.45;
}

.system-tag {
    display: inline-block;
    padding: 3px 10px;
    background: var(--sky-gradient);
    border: 1px solid var(--sky-blue-border);
    border-radius: 4px;
    font-size: 0.76rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    color: var(--sky-blue);
    text-transform: uppercase;
}

/* -------------------------------------------------------------------------
   3. CONFIGURATION PRESET DISPLAY
------------------------------------------------------------------------- */
.preset-details-box {
    background-color: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-left: 3px solid var(--walnut-brown);
    border-radius: 6px;
    padding: 0.75rem 0.9rem;
    margin: 0.4rem 0 0.8rem 0;
}

.preset-weight-line {
    font-size: 0.84rem;
    font-weight: 700;
    color: var(--sky-blue);
    margin-bottom: 0.25rem;
    letter-spacing: 0.01em;
}

.preset-desc-line {
    font-size: 0.82rem;
    color: var(--text-secondary) !important;
    line-height: 1.35;
    margin: 0;
}

.preset-warning-box {
    background-color: var(--accent-red-bg);
    border: 1px solid var(--accent-red-border);
    border-radius: 4px;
    padding: 0.4rem 0.65rem;
    margin-top: 0.4rem;
    font-size: 0.78rem;
    color: var(--accent-red);
    font-weight: 600;
    line-height: 1.35;
}

/* -------------------------------------------------------------------------
   4. BONUS FEATURE COMPONENT
------------------------------------------------------------------------- */
.bonus-banner {
    background-color: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-left: 3px solid var(--walnut-brown);
    border-radius: 0 6px 6px 0;
    padding: 0.75rem 1rem;
    margin: 0.75rem 0;
    box-shadow: var(--card-shadow);
}

.bonus-tag {
    font-size: 0.74rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--sky-blue);
    margin-bottom: 0.15rem;
}

.bonus-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--text-primary) !important;
    margin-bottom: 0.2rem;
}

.bonus-desc {
    font-size: 0.84rem;
    color: var(--text-secondary) !important;
    line-height: 1.35;
    margin: 0;
}

/* -------------------------------------------------------------------------
   5. CANDIDATE SPOTLIGHT CARDS
------------------------------------------------------------------------- */
.spotlight-card {
    background-color: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 1.15rem;
    height: 100%;
    box-shadow: var(--card-shadow);
    position: relative;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.spotlight-card:hover {
    border-color: var(--border-medium);
    box-shadow: var(--card-hover-shadow);
}

.spotlight-card-first,
.spotlight-card-1 {
    border-top: 3px solid var(--accent-red);
}

.spotlight-card-runner,
.spotlight-card-2 {
    border-top: 3px solid var(--walnut-brown);
}

.spotlight-card-3 {
    border-top: 3px solid var(--sky-blue);
}

.spotlight-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}

.spotlight-rank-badge {
    font-size: 0.84rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    letter-spacing: 0.02em;
}

.spotlight-rank-badge-1 {
    background-color: var(--accent-red);
    color: #FFFFFF;
}

.spotlight-rank-badge-2 {
    background-color: var(--walnut-brown);
    color: #FFFFFF;
}

.spotlight-rank-badge-3 {
    background-color: var(--charcoal-surface);
    color: #FFFFFF;
    border: 1px solid var(--sky-blue-border);
}

.spotlight-rank-badge-other {
    background-color: var(--walnut-brown);
    color: #FFFFFF;
}

.spotlight-name {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text-primary) !important;
    margin: 0.2rem 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.spotlight-filename {
    font-size: 0.78rem;
    color: var(--text-muted) !important;
    margin-bottom: 0.6rem;
}

.spotlight-score-display {
    display: flex;
    align-items: baseline;
    gap: 0.4rem;
    margin-bottom: 0.6rem;
}

.spotlight-score-val {
    font-size: 1.9rem;
    font-weight: 700;
    color: var(--text-primary) !important;
    letter-spacing: -0.02em;
}

.spotlight-score-label {
    font-size: 0.8rem;
    color: var(--text-secondary) !important;
    font-weight: 600;
}

.spotlight-rationale {
    font-size: 0.82rem;
    color: var(--text-secondary) !important;
    line-height: 1.45;
    margin: 0.6rem 0;
    padding: 0.5rem 0.65rem;
    background-color: var(--bg-secondary);
    border-radius: 4px;
    border-left: 2px solid var(--walnut-brown);
}

/* -------------------------------------------------------------------------
   6. SKILL CHIPS (MATCHED VS MISSING VS PREFERRED)
------------------------------------------------------------------------- */
.chip-container {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin: 0.3rem 0;
}

.chip {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 0.74rem;
    font-weight: 600;
    line-height: 1.3;
}

.chip-matched {
    background-color: var(--success-green-bg);
    color: var(--success-green);
    border: 1px solid var(--success-green-border);
}

.chip-missing {
    background-color: var(--accent-red-bg);
    color: var(--accent-red);
    border: 1px solid var(--accent-red-border);
}

.chip-preferred {
    background-color: var(--sky-blue-bg);
    color: var(--sky-blue);
    border: 1px solid var(--sky-blue-border);
}

/* -------------------------------------------------------------------------
   7. RECRUITER Q&A ASSISTANT
------------------------------------------------------------------------- */
.qa-card {
    background-color: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 1.25rem;
    margin: 1rem 0;
    box-shadow: var(--card-shadow);
}

.qa-result-card {
    background-color: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-left: 3px solid var(--walnut-brown);
    border-radius: 0 6px 6px 0;
    padding: 1rem 1.15rem;
    margin-top: 1rem;
}

.qa-result-header {
    font-size: 0.76rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--sky-blue);
    margin-bottom: 0.35rem;
}

.qa-result-text {
    font-size: 0.92rem;
    line-height: 1.55;
    color: var(--text-primary) !important;
}

.qa-result-text h3 {
    font-size: 1.05rem;
    margin-top: 0.2rem;
    margin-bottom: 0.5rem;
    color: var(--text-primary) !important;
}

.qa-result-text ul {
    margin: 0.4rem 0;
    padding-left: 1.25rem;
}

.qa-result-text li {
    margin-bottom: 0.35rem;
    color: var(--text-primary) !important;
}
</style>
"""
