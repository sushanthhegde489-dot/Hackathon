"""
app/styles.py - Centralized Dual-Theme Engine (Dark Mode & Light Mode).
Harmonized Palette:
- Dark Mode: Deep slate/dark grey (#111418, #191D24), rich espresso brown (#7A5B45, #3A2B20),
  and light blue mixed shades (#60A5FA, rgba(96, 165, 250, 0.12)), with selective red and green.
- Light Mode: Warm ivory cream (#F7F5F0, #FFFFFF), rich espresso brown (#543E2E, #38281D),
  darker grey typography (#161B22, #4A5463), and light blue mixed accents (#2563EB, #EFF6FF).
Strictly zero emojis. Professional recruiter SaaS aesthetic.
"""

def get_app_css(theme: str = "dark") -> str:
    """Returns the comprehensive CSS stylesheet for either Dark Mode or Light Mode."""
    is_dark = "light" not in theme.lower().strip()

    if is_dark:
        palette_vars = """
    /* -------------------------------------------------------------------------
       DARK MODE: Deep Slate, Rich Espresso Brown & Light Blue Mixed Shades
    ------------------------------------------------------------------------- */
    --bg-main: #111418;
    --bg-surface: #191D24;
    --bg-secondary: #15181F;
    --bg-card: #1F242D;
    --bg-card-hover: rgba(96, 165, 250, 0.08);

    /* Borders: darker grey, rich espresso brown, and subtle light blue mix */
    --border-subtle: #29303D;
    --border-medium: #394354;
    --border-brown: #5A4333;
    --border-blue: #2A4365;

    /* Typography: crisp, readable high contrast */
    --text-primary: #F0F4F8;
    --text-secondary: #9AA8BA;
    --text-muted: #677587;

    /* Rich espresso brown accents */
    --brand-brown: #7A5B45;
    --brand-brown-dark: #3A2B20;
    --brand-brown-light: #9B775C;
    --brand-brown-bg: rgba(122, 91, 69, 0.16);
    --brand-brown-border: rgba(122, 91, 69, 0.35);

    /* Darker grey accents */
    --brand-dark: #242A35;
    --brand-darker: #1A1F27;

    /* Light blue mixed shades */
    --accent-blue: #60A5FA;
    --accent-blue-hover: #3B82F6;
    --accent-blue-bg: rgba(96, 165, 250, 0.12);
    --accent-blue-border: rgba(96, 165, 250, 0.28);
    --accent-blue-subtle: #93C5FD;

    /* Selective red (primary actions & missing critical skills) */
    --accent-red: #E5534B;
    --accent-red-hover: #D13B33;
    --accent-red-bg: rgba(229, 83, 75, 0.16);
    --accent-red-border: rgba(229, 83, 75, 0.35);

    /* Success green */
    --success-green: #3FB950;
    --success-green-bg: rgba(63, 185, 80, 0.14);
    --success-green-border: rgba(63, 185, 80, 0.32);

    /* Table headers, shadows, inputs */
    --table-header-bg: linear-gradient(135deg, #382A20 0%, #1A212C 100%);
    --card-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
    --card-hover-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
    --input-bg: #161A21;
    --input-border: #323B4A;
        """
    else:
        palette_vars = """
    /* -------------------------------------------------------------------------
       LIGHT MODE: Warm Ivory Cream, Rich Brown, Darker Grey & Light Blue
    ------------------------------------------------------------------------- */
    --bg-main: #F7F5F0;
    --bg-surface: #FFFFFF;
    --bg-secondary: #EFECE5;
    --bg-card: #FAF8F5;
    --bg-card-hover: rgba(37, 99, 235, 0.04);

    /* Borders: warmer grey, rich espresso brown, and light blue mix */
    --border-subtle: #DDD5C8;
    --border-medium: #C8BEAF;
    --border-brown: #8D725A;
    --border-blue: #BED6F2;

    /* Typography: darker grey for crisp contrast and readability */
    --text-primary: #161B22;
    --text-secondary: #4A5463;
    --text-muted: #727E8F;

    /* Rich espresso brown accents */
    --brand-brown: #543E2E;
    --brand-brown-dark: #38281D;
    --brand-brown-light: #7B5F4A;
    --brand-brown-bg: #F7F1EB;
    --brand-brown-border: #DBCBBF;

    /* Darker grey accents */
    --brand-dark: #2B3441;
    --brand-darker: #1E2530;

    /* Light blue mixed shades */
    --accent-blue: #2563EB;
    --accent-blue-hover: #1D4ED8;
    --accent-blue-bg: #EFF6FF;
    --accent-blue-border: #BFDBFE;
    --accent-blue-subtle: #3B82F6;

    /* Selective red */
    --accent-red: #A8201A;
    --accent-red-hover: #8C1A15;
    --accent-red-bg: #FCEBEB;
    --accent-red-border: #F7C5C5;

    /* Success green */
    --success-green: #1E6B37;
    --success-green-bg: #EBF5EE;
    --success-green-border: #C6E7CE;

    /* Table headers, shadows, inputs */
    --table-header-bg: linear-gradient(135deg, #3A2A1E 0%, #262F3C 100%);
    --card-shadow: 0 1px 3px rgba(22, 27, 34, 0.05);
    --card-hover-shadow: 0 4px 12px rgba(22, 27, 34, 0.09);
    --input-bg: #FFFFFF;
    --input-border: #C8BEAF;
        """

    return f"""
<style>
/* -------------------------------------------------------------------------
   1. GLOBAL RESETS & THEME CSS VARIABLES
------------------------------------------------------------------------- */
:root {{
{palette_vars}
}}

/* Page background and main typography */
.stApp {{
    background-color: var(--bg-main) !important;
    color: var(--text-primary) !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}}

/* Main container layout */
.main .block-container {{
    max-width: 1200px;
    padding-top: 1.75rem;
    padding-bottom: 4rem;
    padding-left: 2rem;
    padding-right: 2rem;
}}

/* Sidebar styling */
[data-testid="stSidebar"] {{
    background-color: var(--bg-secondary) !important;
    border-right: 1px solid var(--border-subtle) !important;
}}

[data-testid="stSidebar"] hr {{
    border-color: var(--border-subtle) !important;
}}

/* Typography */
h1, h2, h3, h4, h5, h6 {{
    color: var(--text-primary) !important;
    letter-spacing: -0.015em;
    font-weight: 600;
}}

p, span, label {{
    color: var(--text-primary);
}}

/* General Buttons */
.stButton > button {{
    background-color: var(--bg-surface) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-medium) !important;
    border-radius: 6px;
    font-weight: 500;
    font-size: 0.88rem;
    padding: 0.45rem 1rem;
    transition: all 0.15s ease;
    box-shadow: var(--card-shadow);
}}

.stButton > button:hover {{
    background-color: var(--bg-card-hover) !important;
    border-color: var(--accent-blue) !important;
    color: var(--accent-blue) !important;
}}

/* Primary buttons */
.stButton > button[kind="primary"] {{
    background-color: var(--accent-red) !important;
    color: #FFFFFF !important;
    border: 1px solid var(--accent-red) !important;
    font-weight: 600;
}}

.stButton > button[kind="primary"]:hover {{
    background-color: var(--accent-red-hover) !important;
    border-color: var(--accent-red-hover) !important;
    color: #FFFFFF !important;
}}

/* Download buttons */
.stDownloadButton > button {{
    background-color: var(--bg-surface) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-medium) !important;
    border-radius: 6px;
    font-weight: 500;
    font-size: 0.84rem;
    padding: 0.4rem 0.85rem;
}}

.stDownloadButton > button:hover {{
    background-color: var(--bg-card-hover) !important;
    border-color: var(--accent-blue) !important;
    color: var(--accent-blue) !important;
}}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{
    background-color: transparent !important;
    border-bottom: 1px solid var(--border-subtle) !important;
    gap: 1.5rem;
}}

.stTabs [data-baseweb="tab"] {{
    color: var(--text-secondary) !important;
    font-weight: 500;
    font-size: 0.9rem;
    padding: 0.5rem 0.25rem;
    border-bottom: 2px solid transparent;
}}

.stTabs [data-baseweb="tab"][aria-selected="true"] {{
    color: var(--accent-blue) !important;
    font-weight: 600;
    border-bottom: 2px solid var(--accent-blue) !important;
}}

/* Expanders */
.streamlit-expanderHeader {{
    background-color: var(--bg-surface) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: 6px;
    color: var(--text-primary) !important;
    font-weight: 500;
    font-size: 0.9rem;
}}

.streamlit-expanderHeader:hover {{
    border-color: var(--border-medium) !important;
    color: var(--accent-blue) !important;
}}

[data-testid="stExpander"] {{
    border: none;
    margin-bottom: 0.75rem;
}}

/* Inputs, text areas, and selectboxes */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > div {{
    background-color: var(--input-bg) !important;
    border: 1px solid var(--input-border) !important;
    border-radius: 6px !important;
    color: var(--text-primary) !important;
    font-size: 0.9rem !important;
}}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {{
    border-color: var(--accent-blue) !important;
    box-shadow: 0 0 0 1px var(--accent-blue) !important;
}}

/* Selectbox dropdown container & options */
div[data-baseweb="popover"] ul[role="listbox"] {{
    background-color: var(--bg-surface) !important;
    border: 1px solid var(--border-medium) !important;
}}

div[data-baseweb="popover"] li[role="option"] {{
    color: var(--text-primary) !important;
}}

div[data-baseweb="popover"] li[role="option"]:hover {{
    background-color: var(--bg-card-hover) !important;
    color: var(--accent-blue) !important;
}}

/* Radio button text & accent */
[data-testid="stRadio"] label {{
    color: var(--text-primary) !important;
}}

/* Sliders */
div[data-baseweb="slider"] [role="slider"] {{
    background-color: var(--accent-blue) !important;
    border-color: var(--accent-blue) !important;
}}

/* Progress bar */
.stProgress > div > div > div > div {{
    background-color: var(--brand-brown) !important;
}}

/* Custom Alert / Callout Boxes */
.custom-alert {{
    padding: 0.65rem 0.9rem;
    border-radius: 6px;
    font-size: 0.85rem;
    line-height: 1.4;
    margin: 0.5rem 0;
}}

.custom-alert-success {{
    background-color: var(--success-green-bg);
    border: 1px solid var(--success-green-border);
    color: var(--success-green);
}}

.custom-alert-warning {{
    background-color: var(--accent-red-bg);
    border: 1px solid var(--accent-red-border);
    color: var(--accent-red);
    font-weight: 500;
}}

.custom-alert-info {{
    background-color: var(--accent-blue-bg);
    border: 1px solid var(--accent-blue-border);
    color: var(--text-primary);
}}

/* -------------------------------------------------------------------------
   2. HEADER & BRANDING
------------------------------------------------------------------------- */
.app-header {{
    margin-bottom: 1.75rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--border-subtle);
}}

.app-title {{
    font-size: 1.95rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 0.25rem 0;
    letter-spacing: -0.02em;
}}

.app-subtitle {{
    font-size: 0.92rem;
    color: var(--text-secondary);
    margin: 0 0 0.75rem 0;
    line-height: 1.45;
}}

.system-tag {{
    display: inline-block;
    padding: 3px 10px;
    background-color: var(--accent-blue-bg);
    border: 1px solid var(--accent-blue-border);
    border-radius: 4px;
    font-size: 0.76rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    color: var(--accent-blue);
    text-transform: uppercase;
}}

/* -------------------------------------------------------------------------
   3. CONFIGURATION PRESET DISPLAY
------------------------------------------------------------------------- */
.preset-details-box {{
    background-color: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-left: 3px solid var(--brand-brown);
    border-radius: 6px;
    padding: 0.75rem 0.9rem;
    margin: 0.4rem 0 0.8rem 0;
}}

.preset-weight-line {{
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--accent-blue);
    margin-bottom: 0.25rem;
    letter-spacing: 0.01em;
}}

.preset-desc-line {{
    font-size: 0.8rem;
    color: var(--text-secondary);
    line-height: 1.35;
    margin: 0;
}}

.preset-warning-box {{
    background-color: var(--accent-red-bg);
    border: 1px solid var(--accent-red-border);
    border-radius: 4px;
    padding: 0.4rem 0.65rem;
    margin-top: 0.4rem;
    font-size: 0.78rem;
    color: var(--accent-red);
    font-weight: 500;
    line-height: 1.35;
}}

/* -------------------------------------------------------------------------
   4. BONUS FEATURE COMPONENT
------------------------------------------------------------------------- */
.bonus-banner {{
    background-color: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-left: 3px solid var(--brand-brown);
    border-radius: 0 6px 6px 0;
    padding: 0.75rem 1rem;
    margin: 0.75rem 0;
    box-shadow: var(--card-shadow);
}}

.bonus-tag {{
    font-size: 0.74rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--accent-blue);
    margin-bottom: 0.15rem;
}}

.bonus-title {{
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 0.2rem;
}}

.bonus-desc {{
    font-size: 0.82rem;
    color: var(--text-secondary);
    line-height: 1.35;
    margin: 0;
}}

/* -------------------------------------------------------------------------
   5. CANDIDATE SPOTLIGHT CARDS
------------------------------------------------------------------------- */
.spotlight-card {{
    background-color: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 1.1rem;
    height: 100%;
    box-shadow: var(--card-shadow);
    position: relative;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}}

.spotlight-card:hover {{
    border-color: var(--border-medium);
    box-shadow: var(--card-hover-shadow);
}}

.spotlight-card-first,
.spotlight-card-1 {{
    border-top: 3px solid var(--accent-red);
}}

.spotlight-card-runner,
.spotlight-card-2 {{
    border-top: 3px solid var(--brand-brown);
}}

.spotlight-card-3 {{
    border-top: 3px solid var(--accent-blue);
}}

.spotlight-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}}

.spotlight-rank-badge {{
    font-size: 0.82rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    letter-spacing: 0.02em;
}}

.spotlight-rank-badge-1 {{
    background-color: var(--accent-red);
    color: #FFFFFF;
}}

.spotlight-rank-badge-2 {{
    background-color: var(--brand-brown);
    color: #FFFFFF;
}}

.spotlight-rank-badge-3 {{
    background-color: var(--brand-dark);
    color: var(--accent-blue);
    border: 1px solid var(--accent-blue-border);
}}

.spotlight-rank-badge-other {{
    background-color: var(--brand-brown);
    color: #FFFFFF;
}}

.spotlight-name {{
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0.2rem 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}

.spotlight-filename {{
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-bottom: 0.6rem;
}}

.spotlight-score-display {{
    display: flex;
    align-items: baseline;
    gap: 0.4rem;
    margin-bottom: 0.6rem;
}}

.spotlight-score-val {{
    font-size: 1.85rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.02em;
}}

.spotlight-score-label {{
    font-size: 0.78rem;
    color: var(--text-secondary);
    font-weight: 500;
}}

.spotlight-rationale {{
    font-size: 0.8rem;
    color: var(--text-secondary);
    line-height: 1.4;
    margin: 0.6rem 0;
    padding: 0.5rem 0.65rem;
    background-color: var(--bg-secondary);
    border-radius: 4px;
    border-left: 2px solid var(--brand-brown);
}}

/* -------------------------------------------------------------------------
   6. SKILL CHIPS (MATCHED VS MISSING VS PREFERRED)
------------------------------------------------------------------------- */
.chip-container {{
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin: 0.3rem 0;
}}

.chip {{
    display: inline-block;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 0.74rem;
    font-weight: 500;
    line-height: 1.3;
}}

.chip-matched {{
    background-color: var(--success-green-bg);
    color: var(--success-green);
    border: 1px solid var(--success-green-border);
}}

.chip-missing {{
    background-color: var(--accent-red-bg);
    color: var(--accent-red);
    border: 1px solid var(--accent-red-border);
}}

.chip-preferred {{
    background-color: var(--accent-blue-bg);
    color: var(--accent-blue);
    border: 1px solid var(--accent-blue-border);
}}

/* -------------------------------------------------------------------------
   7. FULL RANKED LEADERBOARD TABLE
------------------------------------------------------------------------- */
.leaderboard-container {{
    width: 100%;
    overflow-x: auto;
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    background-color: var(--bg-surface);
    margin: 1rem 0;
    box-shadow: var(--card-shadow);
}}

.leaderboard-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.86rem;
    text-align: left;
}}

.leaderboard-table th {{
    background: var(--table-header-bg);
    color: #FFFFFF;
    font-weight: 600;
    padding: 0.75rem 0.9rem;
    font-size: 0.78rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    border-bottom: 2px solid var(--brand-brown);
    white-space: nowrap;
}}

.leaderboard-table td {{
    padding: 0.7rem 0.9rem;
    border-bottom: 1px solid var(--border-subtle);
    vertical-align: middle;
}}

.leaderboard-table tbody tr:nth-child(even) {{
    background-color: var(--bg-main);
}}

.leaderboard-table tbody tr:nth-child(odd) {{
    background-color: var(--bg-surface);
}}

.leaderboard-table tbody tr:hover {{
    background-color: var(--bg-card-hover) !important;
}}

.cell-rank {{
    font-weight: 700;
    color: var(--brand-brown-light);
    white-space: nowrap;
}}

.cell-candidate {{
    font-weight: 600;
    color: var(--text-primary);
}}

.cell-subtext {{
    font-size: 0.72rem;
    color: var(--text-muted);
    font-weight: 400;
}}

.cell-final-score {{
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--text-primary);
    white-space: nowrap;
}}

.cell-secondary-score {{
    font-size: 0.82rem;
    color: var(--text-secondary);
    white-space: nowrap;
}}

.cell-penalty {{
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--accent-red);
    white-space: nowrap;
}}

.cell-penalty-zero {{
    font-size: 0.82rem;
    color: var(--text-muted);
    white-space: nowrap;
}}

/* -------------------------------------------------------------------------
   8. RECRUITER Q&A ASSISTANT
------------------------------------------------------------------------- */
.qa-card {{
    background-color: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 1.25rem;
    margin: 1rem 0;
    box-shadow: var(--card-shadow);
}}

.qa-suggestions-label {{
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--accent-blue);
    margin-bottom: 0.5rem;
}}

.qa-result-card {{
    background-color: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-left: 3px solid var(--brand-brown);
    border-radius: 0 6px 6px 0;
    padding: 1rem 1.15rem;
    margin-top: 1rem;
}}

.qa-result-header {{
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--accent-blue);
    margin-bottom: 0.35rem;
}}

.qa-result-text {{
    font-size: 0.9rem;
    line-height: 1.5;
    color: var(--text-primary);
}}

.qa-result-text h3 {{
    font-size: 1.05rem;
    margin-top: 0.2rem;
    margin-bottom: 0.5rem;
    color: var(--text-primary);
}}

.qa-result-text ul {{
    margin: 0.4rem 0;
    padding-left: 1.25rem;
}}

.qa-result-text li {{
    margin-bottom: 0.35rem;
    color: var(--text-primary);
}}
</style>
"""
