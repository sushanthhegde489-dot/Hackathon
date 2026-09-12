"""
app/main.py - Smart Candidate Shortlisting Engine
Recruiter Application for End-to-End Hybrid Ranking & Explainability.
Palette: Warm cream, ivory, beige, muted taupe, warm brown, selective red, success green.
Strictly zero emojis. Professional recruiter dashboard aesthetic.
"""

import sys
import time
from pathlib import Path
from typing import List, Optional, Any

# Ensure repository root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd

from app.config import RankingConfig
from app.models import JobDescription, CandidateResult
from app.matching.hybrid_ranker import HybridRanker
from extraction.jd_extractor import JDExtractor
from extraction.resume_extractor import ResumeExtractor
from ingestion.pdf_parser import PDFParser
from app.qa.recruiter_qa import RecruiterQAEngine
from app.bias.jd_bias_detector import JDBiasDetector
from app.styles import get_app_css
from app.ui_helpers import (
    PRESET_CONFIGS,
    SAMPLE_JOB_DESCRIPTIONS,
    check_keyword_stuffing_warning,
    get_demo_resume_paths,
    validate_resume_batch,
    format_percentage,
    generate_leaderboard_csv,
    generate_leaderboard_json
)


@st.cache_data(show_spinner=False)
def parse_jd_from_text(filename: str, text: str) -> JobDescription:
    """Parse raw JD text into structured JobDescription model."""
    return JDExtractor.parse_jd(filename, text)


@st.cache_data(show_spinner=False)
def extract_pdf_text_cached(file_bytes: bytes) -> str:
    """Extract raw text from PDF bytes."""
    return PDFParser.extract_text(file_bytes)


def apply_preset():
    """Callback to apply weights when a preset is selected."""
    preset_name = st.session_state.selected_preset
    preset_data = PRESET_CONFIGS[preset_name]
    st.session_state.kw_weight = preset_data["keyword_weight"]
    st.session_state.req_weight = preset_data["required_skill_weight"]
    st.session_state.noise_threshold = preset_data["semantic_noise_threshold"]
    st.session_state.exp_penalty_rate = preset_data["experience_penalty_per_year"]
    st.session_state.exp_penalty_cap = preset_data["maximum_experience_penalty"]


def render_sidebar() -> RankingConfig:
    """Render the sidebar configuration and return the active ranking config."""
    st.sidebar.markdown("### Interface Theme")
    st.sidebar.radio(
        "Display Mode",
        options=["Dark Mode", "Light Mode"],
        index=0,
        horizontal=True,
        key="theme_mode",
        label_visibility="collapsed",
        help="Toggle between Deep Slate Dark Mode and Warm Neutral Light Mode."
    )
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Calibration & Scoring")

    # Initialize session state for weights if not present
    if "kw_weight" not in st.session_state:
        default_preset = list(PRESET_CONFIGS.keys())[0]
        st.session_state.selected_preset = default_preset
        apply_preset()

    selected_preset = st.sidebar.selectbox(
        "Configuration Preset",
        list(PRESET_CONFIGS.keys()),
        key="selected_preset",
        on_change=apply_preset,
        help="Pre-calibrated scoring profiles."
    )

    preset_data = PRESET_CONFIGS[selected_preset]
    st.sidebar.markdown(
        f'<div class="preset-details-box">'
        f'<div class="preset-weight-line">{preset_data["weights_label"]}</div>'
        f'<div class="preset-desc-line">{preset_data["description"]}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("#### Weight Allocations")

    kw_slider = st.sidebar.slider(
        "Keyword Match Weight ($W_{\\text{kw}}$)",
        min_value=0.0,
        max_value=1.0,
        step=0.05,
        key="kw_weight",
        help="Relative importance of exact canonical skill matching."
    )

    sem_weight = round(1.0 - kw_slider, 2)
    st.sidebar.info(f"Semantic Match Weight ($W_{{\\text{{sem}}}}$): **{sem_weight:.2f}**")

    has_warning, warning_text = check_keyword_stuffing_warning(kw_slider)
    if has_warning:
        st.sidebar.markdown(
            f'<div class="preset-warning-box">{warning_text}</div>',
            unsafe_allow_html=True
        )

    with st.sidebar.expander("Advanced Calibration Parameters", expanded=False):
        req_weight = st.slider(
            "Required Skill Weight",
            min_value=0.50, max_value=0.90,
            step=0.05,
            key="req_weight",
            help="Weight assigned to mandatory skills relative to preferred skills."
        )
        pref_weight = round(1.0 - req_weight, 2)
        st.caption(f"Preferred Skill Weight: **{pref_weight:.2f}**")

        noise_thresh = st.slider(
            "Semantic Noise Threshold ($\\tau$)",
            min_value=0.05, max_value=0.35,
            step=0.01,
            key="noise_threshold",
            help="Cosine similarity floor below which text similarity is mapped to 0.0."
        )
        exp_penalty = st.slider(
            "Experience Penalty Rate (per missing year)",
            min_value=0.01, max_value=0.15,
            step=0.01,
            key="exp_penalty_rate",
            help="Deduction per year candidate falls short of required experience."
        )
        exp_cap = st.slider(
            "Maximum Experience Penalty Cap",
            min_value=0.05, max_value=0.40,
            step=0.05,
            key="exp_penalty_cap",
            help="Maximum total deduction allowed for experience gaps."
        )

    st.sidebar.markdown("---")
    st.sidebar.markdown("#### System Engine Info")
    st.sidebar.caption("**Embedding Model**: `all-MiniLM-L6-v2` (Local CPU)")
    st.sidebar.caption("**Security**: 100% Offline execution, zero external API calls")
    st.sidebar.caption("**Benchmark Target**: 15–18 Candidates per JD")

    return RankingConfig(
        keyword_weight=kw_slider,
        semantic_weight=sem_weight,
        required_skill_weight=req_weight,
        preferred_skill_weight=pref_weight,
        semantic_noise_threshold=noise_thresh,
        experience_penalty_per_year=exp_penalty,
        maximum_experience_penalty=exp_cap
    )


def render_jd_section() -> Optional[JobDescription]:
    """Render the Job Description ingestion UI and return the parsed JD."""
    st.markdown('<div class="section-header">Step 1: Job Description</div>', unsafe_allow_html=True)
    
    current_jd: Optional[JobDescription] = None
    jd_tab1, jd_tab2, jd_tab3 = st.tabs(["Upload JD (PDF)", "Paste JD Text", "Load Sample JD"])

    with jd_tab1:
        uploaded_jd_pdf = st.file_uploader("Upload Job Description PDF", type=["pdf"], key="jd_pdf_uploader")
        if uploaded_jd_pdf:
            try:
                jd_text = extract_pdf_text_cached(uploaded_jd_pdf.read())
                if jd_text:
                    current_jd = parse_jd_from_text(uploaded_jd_pdf.name, jd_text)
                    st.session_state.current_jd = current_jd
                else:
                    st.markdown('<div class="custom-alert custom-alert-warning">Could not extract readable text from the uploaded JD PDF.</div>', unsafe_allow_html=True)
            except Exception as e:
                st.markdown(f'<div class="custom-alert custom-alert-warning">Error parsing uploaded JD PDF: {e}</div>', unsafe_allow_html=True)

    with jd_tab2:
        pasted_jd_text = st.text_area("Paste full Job Description text here:", height=180)
        if st.button("Parse Pasted JD"):
            if pasted_jd_text.strip():
                current_jd = parse_jd_from_text("Pasted_JD.txt", pasted_jd_text)
                st.session_state.current_jd = current_jd
            else:
                st.markdown('<div class="custom-alert custom-alert-warning">Please enter job description text before parsing.</div>', unsafe_allow_html=True)

    with jd_tab3:
        sample_name = st.selectbox("Select Demo Job Description:", list(SAMPLE_JOB_DESCRIPTIONS.keys()))
        if st.button("Load Selected Sample JD"):
            sample_data = SAMPLE_JOB_DESCRIPTIONS[sample_name]
            current_jd = parse_jd_from_text(sample_data["filename"], sample_data["text"])
            st.session_state.current_jd = current_jd

    if "current_jd" in st.session_state and st.session_state.current_jd:
        current_jd = st.session_state.current_jd

    if current_jd:
        st.markdown(
            f'<div class="custom-alert custom-alert-success">'
            f'Active Job Description: <strong>{current_jd.title}</strong> '
            f'(Required Experience: {current_jd.experience_years_required:.1f} yrs | '
            f'Required Skills: {len(current_jd.required_skills)} | '
            f'Preferred Skills: {len(current_jd.preferred_skills)})'
            f'</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="bonus-banner">'
            '<div class="bonus-tag">★ Bonus feature — JD language review</div>'
            '<div class="bonus-desc">Identify potentially narrow or unnecessarily rigid wording in the job description.</div>'
            '</div>',
            unsafe_allow_html=True
        )

        with st.expander("Review detected wording and recommendations", expanded=False):
            bias_report = JDBiasDetector.analyze(current_jd)
            st.caption(
                "This audit evaluates structural clarity and inclusivity. "
                "Findings are informational only and do not modify candidate scores."
            )
            if not bias_report.flags:
                st.markdown(f'<div class="custom-alert custom-alert-success">{bias_report.summary}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="custom-alert custom-alert-info">{bias_report.summary}</div>', unsafe_allow_html=True)
                for flag in bias_report.flags:
                    st.markdown(f"- **{flag.category}** *(Severity: {flag.severity})*: {flag.rationale}")
                    if flag.source_snippet:
                        st.caption(f"  Context: \"{flag.source_snippet}\"")
                    if flag.suggestion:
                        st.caption(f"  Recommendation: {flag.suggestion}")

    return current_jd


def render_resume_section() -> List[Any]:
    """Render the resume ingestion UI and return loaded resumes."""
    st.markdown("---")
    st.markdown('<div class="section-header">Step 2: Batch Resume Processing</div>', unsafe_allow_html=True)
    
    loaded_resumes = []
    res_tab1, res_tab2 = st.tabs(["Load 18 Demo Resumes (Benchmark Corpus)", "Upload Custom PDF Batch"])

    with res_tab1:
        st.caption("Load the curated 18-resume evaluation batch from local storage to verify ranking, explainability, and adversarial defenses.")
        if st.button("Load 18 Demo Resumes", use_container_width=True):
            with st.spinner("Parsing 18 demo PDFs from local storage..."):
                demo_paths = get_demo_resume_paths()
                for path in demo_paths:
                    try:
                        text = extract_pdf_text_cached(path.read_bytes())
                        if text:
                            res = ResumeExtractor.parse_resume(path.name, text)
                            loaded_resumes.append(res)
                    except Exception:
                        pass
                st.session_state.loaded_resumes = loaded_resumes

    with res_tab2:
        uploaded_resumes = st.file_uploader(
            "Upload multiple candidate resumes (PDF)", 
            type=["pdf"], 
            accept_multiple_files=True
        )
        if st.button("Process Uploaded Batch", type="primary"):
            if uploaded_resumes:
                with st.spinner(f"Extracting {len(uploaded_resumes)} resumes..."):
                    for file_obj in uploaded_resumes:
                        try:
                            text = extract_pdf_text_cached(file_obj.read())
                            if text:
                                res = ResumeExtractor.parse_resume(file_obj.name, text)
                                loaded_resumes.append(res)
                        except Exception:
                            pass
                    st.session_state.loaded_resumes = loaded_resumes
            else:
                st.markdown('<div class="custom-alert custom-alert-warning">Please select at least one PDF file to process.</div>', unsafe_allow_html=True)

    if "loaded_resumes" in st.session_state and st.session_state.loaded_resumes:
        loaded_resumes = st.session_state.loaded_resumes
        resume_items = [(r.filename, r.raw_text) for r in loaded_resumes]
        validation_report = validate_resume_batch(resume_items)
        st.markdown(
            f'<div class="custom-alert custom-alert-success">{validation_report["valid_count"]} candidate resumes parsed and ready for ranking.</div>',
            unsafe_allow_html=True
        )

        if validation_report["has_empty"]:
            st.markdown(
                f'<div class="custom-alert custom-alert-warning">{len(validation_report["empty_files"])} resume(s) yielded no readable text: {", ".join(validation_report["empty_files"])}</div>',
                unsafe_allow_html=True
            )
        if validation_report["has_duplicates"]:
            st.markdown(
                f'<div class="custom-alert custom-alert-warning">Duplicate filenames detected: {", ".join(validation_report["duplicates"])}</div>',
                unsafe_allow_html=True
            )
                
    return loaded_resumes


def render_top_spotlights(ranked_results: List[CandidateResult]):
    """Render the Top 3 candidate spotlight cards with explicit #1, #2, #3 labels."""
    st.markdown('<div class="section-header">Candidate Spotlight</div>', unsafe_allow_html=True)
    top3 = ranked_results[:3]

    cols = st.columns(min(3, len(top3)))
    for i, cand in enumerate(top3):
        rank_num = i + 1
        rank_label = f"#{rank_num}"
        card_class = f"spotlight-card spotlight-card-{rank_num}"
        badge_class = f"spotlight-rank-badge spotlight-rank-badge-{rank_num}"

        matched_req = cand.keyword_breakdown.matched_required_skills
        missing_req = cand.keyword_breakdown.missing_required_skills
        matched_pref = cand.keyword_breakdown.matched_preferred_skills

        with cols[i]:
            chips_html = '<div class="chip-container">'
            for s in matched_req:
                chips_html += f'<span class="chip chip-matched">{s}</span>'
            for s in missing_req:
                chips_html += f'<span class="chip chip-missing">missing: {s}</span>'
            for s in matched_pref:
                chips_html += f'<span class="chip chip-preferred">{s}</span>'
            chips_html += '</div>'

            st.markdown(
                f'<div class="{card_class}">'
                f'<div class="spotlight-header">'
                f'<span class="{badge_class}">{rank_label}</span>'
                f'<span style="font-size: 0.78rem; color: var(--text-secondary); font-weight: 500;">{cand.resume.experience_years:.1f} yrs exp</span>'
                f'</div>'
                f'<div class="spotlight-name" title="{cand.resume.candidate_name}">{cand.resume.candidate_name}</div>'
                f'<div class="spotlight-filename">{cand.resume.filename}</div>'
                f'<div class="spotlight-score-display">'
                f'<span class="spotlight-score-val">{format_percentage(cand.final_score)}</span>'
                f'<span class="spotlight-score-label">Final Score</span>'
                f'</div>'
                f'<div class="spotlight-rationale">{cand.ranking_reason}</div>'
                f'<div style="font-size: 0.76rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; color: var(--accent-blue); margin-top: 0.5rem;">Skills Evaluation</div>'
                f'{chips_html}'
                f'</div>',
                unsafe_allow_html=True
            )

            with st.expander(f"Requirement Evidence Table ({rank_label})", expanded=False):
                evidence = cand.keyword_breakdown.evidence
                req_skills = matched_req + missing_req
                if req_skills:
                    evidence_rows = []
                    for req in req_skills:
                        item = evidence.get(req, {})
                        is_matched = item.get("status") == "matched"
                        evidence_rows.append({
                            "Requirement": req,
                            "Status": "Found" if is_matched else "Missing",
                            "Source Section": item.get("source_section", "—"),
                            "Evidence Snippet": item.get("source_context", "—")
                        })
                    st.table(pd.DataFrame(evidence_rows))
                else:
                    st.caption("No explicit required skills in Job Description.")


def render_leaderboard(ranked_results: List[CandidateResult]):
    """Render the full candidate leaderboard in a polished recruiter table."""
    st.markdown("---")
    st.markdown('<div class="section-header">Full Ranked Leaderboard</div>', unsafe_allow_html=True)

    search_query = st.text_input("Search leaderboard by candidate name or skill:", "").strip().lower()

    filtered_results = []
    for rank, res in enumerate(ranked_results, 1):
        res.rank = rank
        name = res.resume.candidate_name
        skills_str = ", ".join(res.matched_skills)
        if search_query and (search_query not in name.lower() and search_query not in skills_str.lower()):
            continue
        filtered_results.append((rank, res))

    if not filtered_results:
        st.markdown('<div class="custom-alert custom-alert-info">No candidates match your search query.</div>', unsafe_allow_html=True)
    else:
        # Build custom HTML table with dark brown header and beige alternating rows
        rows_html = ""
        for rank, res in filtered_results:
            diag = res.diagnostics
            pen = res.penalties.total_penalty
            pen_class = "cell-penalty" if pen > 0.0 else "cell-penalty-zero"
            pen_display = f"-{format_percentage(pen)}" if pen > 0.0 else "0.0%"

            # Chips for required matched and missing
            chips = ""
            matched_req = res.keyword_breakdown.matched_required_skills
            missing_req = res.keyword_breakdown.missing_required_skills
            for s in matched_req[:2]:
                chips += f'<span class="chip chip-matched">{s}</span>'
            for s in missing_req[:2]:
                chips += f'<span class="chip chip-missing">{s}</span>'

            rows_html += f"""
            <tr>
                <td class="cell-rank">#{rank}</td>
                <td class="cell-candidate">
                    <div>{res.resume.candidate_name}</div>
                    <div class="cell-subtext">{res.resume.filename}</div>
                </td>
                <td class="cell-final-score">{format_percentage(res.final_score)}</td>
                <td class="cell-secondary-score">{format_percentage(diag.keyword_score)}</td>
                <td class="cell-secondary-score">{format_percentage(diag.semantic_score)}</td>
                <td class="{pen_class}">{pen_display}</td>
                <td><div class="chip-container">{chips}</div></td>
            </tr>
            """

        table_html = f"""
        <div class="leaderboard-container">
            <table class="leaderboard-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Candidate</th>
                        <th>Final Score</th>
                        <th>Keyword</th>
                        <th>Semantic</th>
                        <th>Experience Penalty</th>
                        <th>Key Skills Overview</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        """
        st.markdown(table_html, unsafe_allow_html=True)

    col1, col2, _ = st.columns([2.5, 2.5, 3])
    with col1:
        st.download_button(
            label="Export Leaderboard to CSV",
            data=generate_leaderboard_csv(ranked_results),
            file_name=f"shortlisting_leaderboard_{int(time.time())}.csv",
            mime="text/csv",
            use_container_width=True
        )
    with col2:
        st.download_button(
            label="Export Leaderboard to JSON",
            data=generate_leaderboard_json(ranked_results),
            file_name=f"shortlisting_leaderboard_{int(time.time())}.json",
            mime="application/json",
            use_container_width=True
        )


def render_qa_assistant(ranked_results: List[CandidateResult], current_jd: JobDescription):
    """Render the Recruiter Q&A Assistant with 4 working suggested queries."""
    st.markdown("---")
    st.markdown(
        '<div class="bonus-banner">'
        '<div class="bonus-tag">★ Bonus feature — Recruiter Q&A</div>'
        '<div class="bonus-desc">Ask evidence-based questions about candidate rankings and skill gaps.</div>'
        '</div>',
        unsafe_allow_html=True
    )

    qa_engine = RecruiterQAEngine(ranked_results, current_jd)
    suggested_questions = qa_engine.get_suggested_questions()

    if "active_qa_query" not in st.session_state:
        st.session_state.active_qa_query = ""

    st.markdown('<div class="qa-suggestions-label">Suggested Questions</div>', unsafe_allow_html=True)

    # 4 distinct question buttons in 2 columns
    q_cols = st.columns(2)
    for i, q_text in enumerate(suggested_questions[:4]):
        col_idx = i % 2
        if q_cols[col_idx].button(q_text, key=f"btn_qa_suggest_{i}", use_container_width=True):
            st.session_state.active_qa_query = q_text

    user_query = st.text_input(
        "Or enter a custom question:",
        value=st.session_state.active_qa_query,
        placeholder="e.g. Why did #1 rank above #2?",
        key="qa_input_box"
    )

    query_to_execute = user_query.strip() or st.session_state.active_qa_query.strip()

    if query_to_execute:
        qa_resp = qa_engine.answer_query(query_to_execute)
        st.markdown(
            f'<div class="qa-result-card">'
            f'<div class="qa-result-header">Query: {query_to_execute}</div>'
            f'<div class="qa-result-text">{qa_resp.answer}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        if qa_resp.supporting_evidence:
            with st.expander("View Verifiable Data Provenance", expanded=False):
                st.json(qa_resp.supporting_evidence)


def render_deep_dive(ranked_results: List[CandidateResult]):
    """Render the expandable deep dive inspector for each candidate."""
    st.markdown("---")
    st.markdown('<div class="section-header">Deep-Dive Candidate Inspector</div>', unsafe_allow_html=True)

    for rank, cand in enumerate(ranked_results, 1):
        title = f"#{rank}: {cand.resume.candidate_name} — Final Score: {format_percentage(cand.final_score)} ({cand.resume.filename})"
        with st.expander(title, expanded=False):
            tab1, tab2, tab3 = st.tabs(["Decision Provenance", "Score Breakdown", "Extracted Resume Text"])

            with tab1:
                st.markdown("**Ranking Rationale:**")
                st.markdown(f'<div class="custom-alert custom-alert-info">{cand.ranking_reason}</div>', unsafe_allow_html=True)
                st.write(f"**Experience & Deductions:** {cand.resume.experience_years:.1f} yrs experience | Penalty: {cand.penalties.total_penalty:.4f}")

            with tab2:
                diag = cand.diagnostics
                st.markdown("**Mathematical Decomposition:**")
                st.latex(
                    rf"S_{{\text{{final}}}} = \min\left(1.0, \max(0.0, "
                    rf"{diag.keyword_score:.3f} \times {diag.keyword_weight:.2f} + "
                    rf"{diag.semantic_score:.3f} \times {diag.semantic_weight:.2f} - "
                    rf"{diag.total_penalty:.3f})\right) = {cand.final_score:.4f}"
                )
                
                if cand.semantic_breakdown.strongest_matches:
                    st.markdown("**Top Semantic Alignments:**")
                    for m in cand.semantic_breakdown.strongest_matches[:3]:
                        st.markdown(f"- **Section `{m.get('resume_section', 'general')}`** (Similarity: `{m.get('similarity', 0.0):.3f}`): {m.get('resume_snippet', '')}")

            with tab3:
                st.text_area("Raw Extracted Text", cand.resume.raw_text, height=180, disabled=True, key=f"raw_text_{rank}")


def main():
    """Main application entrypoint."""
    st.set_page_config(
        page_title="Smart Candidate Shortlisting Engine",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Determine active theme (defaults to Dark Mode)
    active_theme = "dark" if st.session_state.get("theme_mode", "Dark Mode") == "Dark Mode" else "light"

    # Inject centralized stylesheet (Dark Mode or Light Mode)
    st.markdown(get_app_css(theme=active_theme), unsafe_allow_html=True)

    # App header
    st.markdown(
        '<div class="app-header">'
        '<h1 class="app-title">Smart Candidate Shortlisting Engine</h1>'
        '<div class="app-subtitle">Explainable hybrid matching combining explicit skills, contextual semantic embeddings, and calibrated experience penalties.</div>'
        '<span class="system-tag">100% Offline Local Engine — Zero External API Calls</span>'
        '</div>',
        unsafe_allow_html=True
    )

    active_config = render_sidebar()
    current_jd = render_jd_section()
    
    if not current_jd:
        st.markdown('<div class="custom-alert custom-alert-info">Select or upload a Job Description above to evaluate candidates.</div>', unsafe_allow_html=True)
        return

    loaded_resumes = render_resume_section()

    if loaded_resumes and current_jd:
        if st.button("Rank Resumes Against Job Description", type="primary", use_container_width=True):
            with st.spinner("Scoring and ranking candidates..."):
                ranked_results = HybridRanker.rank_batch(current_jd, loaded_resumes, config=active_config)
                st.session_state.ranked_results = ranked_results

        if "ranked_results" in st.session_state and st.session_state.ranked_results:
            ranked_results = st.session_state.ranked_results
            
            st.markdown("---")
            render_top_spotlights(ranked_results)
            render_leaderboard(ranked_results)
            render_qa_assistant(ranked_results, current_jd)
            render_deep_dive(ranked_results)


if __name__ == "__main__":
    main()

