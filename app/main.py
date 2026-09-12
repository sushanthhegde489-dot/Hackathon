"""
app/main.py - Smart Candidate Shortlisting Engine
Recruiter Streamlit Application for End-to-End Hybrid Ranking & Explainability.
"""

import io
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Ensure repository root is on sys.path so 'app', 'extraction', 'ingestion' packages are importable
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd

from app.config import RankingConfig, DEFAULT_RANKING_CONFIG, DEFAULT_EMBEDDING_MODEL
from app.models import JobDescription, Resume, CandidateResult
from app.matching.hybrid_ranker import HybridRanker
from extraction.jd_extractor import JDExtractor
from extraction.resume_extractor import ResumeExtractor
from ingestion.pdf_parser import PDFParser
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

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION & STYLING
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="Smart Candidate Shortlisting Engine",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for polished recruiter dashboard
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .badge-offline {
        display: inline-block;
        background-color: #DCFCE7;
        color: #166534;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    .card-top1 {
        background: linear-gradient(135deg, #FEF9C3 0%, #FEF08A 100%);
        border: 1px solid #FACC15;
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    .card-top2 {
        background: linear-gradient(135deg, #F1F5F9 0%, #E2E8F0 100%);
        border: 1px solid #CBD5E1;
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    .card-top3 {
        background: linear-gradient(135deg, #FFEDD5 0%, #FED7AA 100%);
        border: 1px solid #FDBA74;
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    .skill-pill-req {
        display: inline-block;
        background-color: #DCFCE7;
        color: #15803D;
        padding: 0.2rem 0.5rem;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 2px;
    }
    .skill-pill-pref {
        display: inline-block;
        background-color: #DBEAFE;
        color: #1D4ED8;
        padding: 0.2rem 0.5rem;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 2px;
    }
    .skill-pill-miss {
        display: inline-block;
        background-color: #FEE2E2;
        color: #B91C1C;
        padding: 0.2rem 0.5rem;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 2px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# CACHED PARSING & PIPELINE FUNCTIONS
# -----------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def parse_jd_from_text(filename: str, text: str) -> JobDescription:
    """Parses raw JD text into structured JobDescription model."""
    return JDExtractor.parse_jd(filename, text)

@st.cache_data(show_spinner=False)
def parse_resume_from_text(filename: str, text: str) -> Resume:
    """Parses raw Resume text into structured Resume model."""
    return ResumeExtractor.parse_resume(filename, text)

@st.cache_data(show_spinner=False)
def extract_pdf_text_cached(filename: str, file_bytes: bytes) -> str:
    """Extracts raw text from PDF bytes."""
    return PDFParser.extract_text(file_bytes)

# -----------------------------------------------------------------------------
# SIDEBAR CONTROLS & CALIBRATION PRESETS
# -----------------------------------------------------------------------------

st.sidebar.markdown("### ⚙️ Calibration & Scoring")

# 1. Preset Selector
selected_preset = st.sidebar.selectbox(
    "Configuration Preset",
    list(PRESET_CONFIGS.keys()),
    index=0,
    help="Pre-calibrated weight profiles. 'Recommended' balances keywords and semantic context."
)

preset_data = PRESET_CONFIGS[selected_preset]
st.sidebar.caption(preset_data["description"])

# Initialize default values in session state for synchronization
if "prev_preset" not in st.session_state:
    st.session_state.prev_preset = selected_preset
    st.session_state.kw_weight = preset_data["keyword_weight"]
    st.session_state.sem_weight = preset_data["semantic_weight"]
    st.session_state.req_weight = preset_data["required_skill_weight"]
    st.session_state.pref_weight = preset_data["preferred_skill_weight"]
    st.session_state.noise_threshold = preset_data["semantic_noise_threshold"]
    st.session_state.exp_penalty_rate = preset_data["experience_penalty_per_year"]
    st.session_state.exp_penalty_cap = preset_data["maximum_experience_penalty"]

# If preset changed, update session state values
if st.session_state.prev_preset != selected_preset:
    st.session_state.kw_weight = preset_data["keyword_weight"]
    st.session_state.sem_weight = preset_data["semantic_weight"]
    st.session_state.req_weight = preset_data["required_skill_weight"]
    st.session_state.pref_weight = preset_data["preferred_skill_weight"]
    st.session_state.noise_threshold = preset_data["semantic_noise_threshold"]
    st.session_state.exp_penalty_rate = preset_data["experience_penalty_per_year"]
    st.session_state.exp_penalty_cap = preset_data["maximum_experience_penalty"]
    st.session_state.prev_preset = selected_preset

# Fine-tuning Sliders
st.sidebar.markdown("---")
st.sidebar.markdown("#### Weight Allocations")

kw_slider = st.sidebar.slider(
    "Keyword Match Weight ($W_{\\text{kw}}$)",
    min_value=0.0,
    max_value=1.0,
    value=float(st.session_state.kw_weight),
    step=0.05,
    help="Relative importance of exact canonical skill matching."
)

# Semantic weight is automatically 1.0 - kw_slider
sem_weight = round(1.0 - kw_slider, 2)
st.sidebar.info(f"Semantic Match Weight ($W_{{\\text{{sem}}}}$): **{sem_weight:.2f}**")

# Check adversarial stuffing warning
has_warning, warning_text = check_keyword_stuffing_warning(kw_slider)
if has_warning:
    st.sidebar.warning(warning_text)

with st.sidebar.expander("🛠️ Advanced Calibration Parameters", expanded=False):
    req_weight = st.slider(
        "Required Skill Weight",
        min_value=0.50,
        max_value=0.90,
        value=float(st.session_state.req_weight),
        step=0.05,
        help="Weight assigned to mandatory skills relative to preferred skills."
    )
    pref_weight = round(1.0 - req_weight, 2)
    st.caption(f"Preferred Skill Weight: **{pref_weight:.2f}**")

    noise_thresh = st.slider(
        "Semantic Noise Threshold ($\\tau$)",
        min_value=0.05,
        max_value=0.35,
        value=float(st.session_state.noise_threshold),
        step=0.01,
        help="Cosine similarity floor below which text similarity is mapped to 0.0."
    )

    exp_penalty = st.slider(
        "Experience Penalty Rate (per missing year)",
        min_value=0.01,
        max_value=0.15,
        value=float(st.session_state.exp_penalty_rate),
        step=0.01,
        help="Deduction per year candidate falls short of required experience."
    )

    exp_cap = st.slider(
        "Maximum Experience Penalty Cap",
        min_value=0.05,
        max_value=0.40,
        value=float(st.session_state.exp_penalty_cap),
        step=0.05,
        help="Maximum total deduction allowed for experience gaps."
    )

# Active Ranking Configuration
active_config = RankingConfig(
    keyword_weight=kw_slider,
    semantic_weight=sem_weight,
    required_skill_weight=req_weight,
    preferred_skill_weight=pref_weight,
    semantic_noise_threshold=noise_thresh,
    experience_penalty_per_year=exp_penalty,
    maximum_experience_penalty=exp_cap
)

st.sidebar.markdown("---")
st.sidebar.markdown("#### System Engine Info")
st.sidebar.caption("⚡ **Embedding Model**: `all-MiniLM-L6-v2` (Local CPU)")
st.sidebar.caption("🔒 **Security**: 100% Offline execution, no external API calls")
st.sidebar.caption("📊 **Benchmark Target**: 15–18 Candidates per JD")

# -----------------------------------------------------------------------------
# MAIN APPLICATION INTERFACE
# -----------------------------------------------------------------------------

st.markdown('<div class="main-header">🎯 Smart Candidate Shortlisting Engine</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Explainable, local hybrid matching combining explicit canonical skills, '
    'contextual semantic embeddings, and calibrated experience penalties.</div>',
    unsafe_allow_html=True
)
st.markdown('<div class="badge-offline">🟢 100% Offline Local Engine — No LLM / API Dependency</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# STEP 1: JOB DESCRIPTION INPUT
# -----------------------------------------------------------------------------

st.markdown("### Step 1: Job Description")

jd_tab1, jd_tab2, jd_tab3 = st.tabs(["📄 Upload JD (PDF)", "✍️ Paste JD Text", "📚 Load Sample JD"])

current_jd: Optional[JobDescription] = None

with jd_tab1:
    uploaded_jd_pdf = st.file_uploader("Upload Job Description PDF", type=["pdf"], key="jd_pdf_uploader")
    if uploaded_jd_pdf is not None:
        try:
            jd_bytes = uploaded_jd_pdf.read()
            jd_text = extract_pdf_text_cached(uploaded_jd_pdf.name, jd_bytes)
            if jd_text:
                current_jd = parse_jd_from_text(uploaded_jd_pdf.name, jd_text)
            else:
                st.error("Could not extract readable text from the uploaded JD PDF.")
        except Exception as e:
            st.error(f"Error parsing uploaded JD PDF: {e}")

with jd_tab2:
    pasted_jd_text = st.text_area(
        "Paste Job Description Text",
        height=180,
        placeholder="Job Title: ... \nExperience Required: ... \nRequired Skills: ...",
        key="jd_text_area"
    )
    if pasted_jd_text.strip() and uploaded_jd_pdf is None:
        current_jd = parse_jd_from_text("pasted_jd.txt", pasted_jd_text.strip())

with jd_tab3:
    sample_jd_name = st.selectbox("Select Pre-Loaded Sample JD", list(SAMPLE_JOB_DESCRIPTIONS.keys()))
    if st.button("Load Selected Sample JD", key="load_sample_jd_btn"):
        sample_data = SAMPLE_JOB_DESCRIPTIONS[sample_jd_name]
        st.session_state["loaded_sample_jd"] = sample_data
        st.rerun()

    if "loaded_sample_jd" in st.session_state and uploaded_jd_pdf is None and not pasted_jd_text.strip():
        sample = st.session_state["loaded_sample_jd"]
        current_jd = parse_jd_from_text(sample["filename"], sample["text"])

# Display Parsed JD Card if JD exists
if current_jd:
    with st.container():
        st.markdown(f"#### 📋 Parsed Job Profile: **{current_jd.title}**")
        col_jd1, col_jd2, col_jd3 = st.columns([1.5, 3, 3])
        with col_jd1:
            st.metric("Experience Required", f"{current_jd.experience_years_required:.1f} Years")
            st.caption(f"Source: `{current_jd.filename}`")
        with col_jd2:
            st.markdown("**Required Skills:**")
            if current_jd.required_skills:
                pills = " ".join([f'<span class="skill-pill-req">{s}</span>' for s in current_jd.required_skills])
                st.markdown(pills, unsafe_allow_html=True)
            else:
                st.write("None detected")
        with col_jd3:
            st.markdown("**Preferred Skills:**")
            if current_jd.preferred_skills:
                pills = " ".join([f'<span class="skill-pill-pref">{s}</span>' for s in current_jd.preferred_skills])
                st.markdown(pills, unsafe_allow_html=True)
            else:
                st.write("None detected")
else:
    st.info("👋 Please upload a Job Description PDF, paste text, or load a Sample JD to begin.")

# -----------------------------------------------------------------------------
# STEP 2: RESUMES INPUT (15–18 CANDIDATES)
# -----------------------------------------------------------------------------

st.markdown("---")
st.markdown("### Step 2: Candidate Resumes")

resume_tab1, resume_tab2 = st.tabs(["📤 Upload Resumes (PDFs)", "📂 Load Curated Demo Candidates (18 PDFs)"])

raw_resume_items: List[Tuple[str, str]] = []

with resume_tab1:
    uploaded_resumes = st.file_uploader(
        "Upload Candidate Resumes (PDF)",
        type=["pdf"],
        accept_multiple_files=True,
        key="resume_uploader",
        help="Upload 15 to 18 PDF resumes for comprehensive ranking evaluation."
    )
    if uploaded_resumes:
        for f in uploaded_resumes:
            try:
                f_bytes = f.read()
                txt = extract_pdf_text_cached(f.name, f_bytes)
                raw_resume_items.append((f.name, txt))
            except Exception as e:
                raw_resume_items.append((f.name, ""))

with resume_tab2:
    st.markdown("Load a diverse, curated set of **18 real resumes** directly from `data/resumes/`.")
    if st.button("Load 18 Demo Resumes", key="load_demo_btn"):
        demo_paths = get_demo_resume_paths(target_count=18)
        st.session_state["demo_resumes_loaded"] = True
        st.session_state["demo_paths"] = [str(p) for p in demo_paths]
        st.rerun()

    if st.session_state.get("demo_resumes_loaded", False) and not uploaded_resumes:
        paths = [Path(p) for p in st.session_state.get("demo_paths", [])]
        for p in paths:
            if p.exists():
                txt = PDFParser.extract_text(p)
                raw_resume_items.append((p.name, txt))

# Batch Validation and Health Inspection
if raw_resume_items:
    validation = validate_resume_batch(raw_resume_items)
    
    col_v1, col_v2, col_v3 = st.columns([1.5, 2.5, 4])
    with col_v1:
        st.metric("Loaded Resumes", f"{validation['total_count']}")
    with col_v2:
        if validation["count_status"] == "optimal":
            st.success(f"✅ {validation['count_message']}")
        elif validation["count_status"] == "below_optimal":
            st.warning(f"⚠️ {validation['count_message']}")
        else:
            st.info(f"ℹ️ {validation['count_message']}")
    with col_v3:
        if validation["has_empty"]:
            st.error(f"Unreadable/Empty PDFs ({len(validation['empty_files'])}): {', '.join(validation['empty_files'])}")
        elif validation["has_duplicates"]:
            st.warning(f"Duplicate files detected: {', '.join(validation['duplicates'])}")
        else:
            st.success("All candidate files parsed successfully.")

# -----------------------------------------------------------------------------
# STEP 3: HYBRID RANKING PIPELINE EXECUTION
# -----------------------------------------------------------------------------

if current_jd and raw_resume_items:
    # Filter valid non-empty resumes
    valid_resumes = [parse_resume_from_text(fn, txt) for fn, txt in raw_resume_items if txt and txt.strip()]

    if valid_resumes:
        with st.spinner("⚡ Running local hybrid ranking pipeline..."):
            ranked_results: List[CandidateResult] = HybridRanker.rank_batch(
                current_jd,
                valid_resumes,
                active_config
            )

        st.markdown("---")
        st.markdown("### Step 3: Candidate Leaderboard & Explainability")

        # ---------------------------------------------------------------------
        # TOP 3 SPOTLIGHT CARDS
        # ---------------------------------------------------------------------
        if len(ranked_results) >= 3:
            st.markdown("#### 🌟 Top 3 Candidate Spotlight")
            top_cols = st.columns(3)
            medals = ["🥇 Rank 1", "🥈 Rank 2", "🥉 Rank 3"]
            styles = ["card-top1", "card-top2", "card-top3"]

            for idx in range(3):
                cand = ranked_results[idx]
                diag = cand.diagnostics
                kw = cand.keyword_breakdown
                sem = cand.semantic_breakdown
                pen = cand.penalties

                with top_cols[idx]:
                    st.markdown(f'<div class="{styles[idx]}">', unsafe_allow_html=True)
                    st.markdown(f"### {medals[idx]}")
                    st.markdown(f"**{cand.resume.candidate_name}** (`{cand.resume.filename}`)")
                    st.markdown(f"## **{format_percentage(cand.final_score)}**")
                    st.caption(f"Base: {format_percentage(diag.base_score)} | Exp: {cand.resume.experience_years:.1f} yrs")

                    st.markdown("---")
                    st.markdown("**Score Decomposition:**")
                    st.progress(min(1.0, cand.final_score))
                    st.caption(
                        f"KW Contribution: **{diag.keyword_contribution:.3f}** "
                        f"({diag.keyword_score:.2f} × {diag.keyword_weight:.2f})<br>"
                        f"Sem Contribution: **{diag.semantic_contribution:.3f}** "
                        f"({diag.semantic_score:.2f} × {diag.semantic_weight:.2f})<br>"
                        f"Exp Penalty: **-{diag.total_penalty:.3f}**",
                        unsafe_allow_html=True
                    )

                    st.markdown("**Matched Required Skills:**")
                    if kw.matched_required_skills:
                        pills = " ".join([f'<span class="skill-pill-req">{s}</span>' for s in kw.matched_required_skills])
                        st.markdown(pills, unsafe_allow_html=True)
                    else:
                        st.write("None")

                    if kw.missing_required_skills:
                        st.markdown("**Missing Required Skills:**")
                        pills = " ".join([f'<span class="skill-pill-miss">{s}</span>' for s in kw.missing_required_skills])
                        st.markdown(pills, unsafe_allow_html=True)

                    if kw.matched_preferred_skills:
                        st.markdown("**Preferred Skills:**")
                        pills = " ".join([f'<span class="skill-pill-pref">{s}</span>' for s in kw.matched_preferred_skills])
                        st.markdown(pills, unsafe_allow_html=True)

                    if sem.strongest_matches:
                        top_sem = sem.strongest_matches[0]
                        st.markdown(f"**Top Semantic Match** ({top_sem.get('similarity', 0.0):.2f}):")
                        st.caption(f"_{top_sem.get('resume_snippet', '')[:140]}..._")

                    st.markdown("</div>", unsafe_allow_html=True)

        # ---------------------------------------------------------------------
        # FULL CANDIDATE LEADERBOARD (ALL 15–18 CANDIDATES)
        # ---------------------------------------------------------------------
        st.markdown("---")
        st.markdown("#### 📊 Full Ranked Leaderboard (All Candidates)")

        # Search / filter candidates
        search_query = st.text_input("🔍 Search Leaderboard by candidate name or skill", "").strip().lower()

        table_rows = []
        for rank, res in enumerate(ranked_results, 1):
            name = res.resume.candidate_name
            skills_str = ", ".join(res.matched_skills)
            
            # Apply search filter
            if search_query and (search_query not in name.lower() and search_query not in skills_str.lower()):
                continue

            diag = res.diagnostics
            table_rows.append({
                "Rank": rank,
                "Candidate Name": name,
                "Filename": res.resume.filename,
                "Final Score": format_percentage(res.final_score),
                "Base Score": format_percentage(diag.base_score),
                "Keyword Score": format_percentage(diag.keyword_score),
                "Semantic Score": format_percentage(diag.semantic_score),
                "Experience": f"{res.resume.experience_years:.1f} yrs",
                "Penalty": format_percentage(diag.total_penalty),
                "Matched Skills": ", ".join(res.matched_skills) if res.matched_skills else "None"
            })

        if table_rows:
            df = pd.DataFrame(table_rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No candidates match your search query.")

        # Export Buttons
        col_exp1, col_exp2, _ = st.columns([2, 2, 4])
        with col_exp1:
            csv_data = generate_leaderboard_csv(ranked_results)
            st.download_button(
                label="📥 Export Leaderboard to CSV",
                data=csv_data,
                file_name=f"shortlisting_leaderboard_{int(time.time())}.csv",
                mime="text/csv"
            )
        with col_exp2:
            json_data = generate_leaderboard_json(ranked_results)
            st.download_button(
                label="📥 Export Leaderboard to JSON",
                data=json_data,
                file_name=f"shortlisting_leaderboard_{int(time.time())}.json",
                mime="application/json"
            )

        # ---------------------------------------------------------------------
        # INDIVIDUAL CANDIDATE INSPECTION (EXPANDABLE DETAILS)
        # ---------------------------------------------------------------------
        st.markdown("---")
        st.markdown("#### 🔍 Deep-Dive Candidate Inspector")

        for rank, cand in enumerate(ranked_results, 1):
            with st.expander(
                f"#{rank}: {cand.resume.candidate_name} — Final Score: {format_percentage(cand.final_score)} "
                f"({cand.resume.filename})"
            ):
                tab_exp1, tab_exp2, tab_exp3 = st.tabs(["📝 Decision Provenance", "🔬 Score Breakdown", "📄 Extracted Resume Text"])

                with tab_exp1:
                    st.markdown("**Ranking Rationale:**")
                    st.info(cand.ranking_reason)

                    col_det1, col_det2 = st.columns(2)
                    with col_det1:
                        st.markdown("**Matched Required Skills:**")
                        st.write(", ".join(cand.keyword_breakdown.matched_required_skills) or "None")
                        st.markdown("**Missing Required Skills:**")
                        st.write(", ".join(cand.keyword_breakdown.missing_required_skills) or "None")
                    with col_det2:
                        st.markdown("**Matched Preferred Skills:**")
                        st.write(", ".join(cand.keyword_breakdown.matched_preferred_skills) or "None")
                        st.markdown("**Experience & Penalty:**")
                        st.write(
                            f"{cand.resume.experience_years:.1f} yrs experience | "
                            f"Penalty: {cand.penalties.total_penalty:.4f}"
                        )

                with tab_exp2:
                    diag = cand.diagnostics
                    st.markdown("**Mathematical Decomposition:**")
                    st.latex(
                        rf"S_{{\text{{final}}}} = \min\left(1.0, \max(0.0, "
                        rf"{diag.keyword_score:.3f} \times {diag.keyword_weight:.2f} + "
                        rf"{diag.semantic_score:.3f} \times {diag.semantic_weight:.2f} - "
                        rf"{diag.total_penalty:.3f})\right) = {cand.final_score:.4f}"
                    )

                    st.markdown("**Top Semantic Alignments:**")
                    for m in cand.semantic_breakdown.strongest_matches[:3]:
                        st.markdown(
                            f"- **Section `{m.get('resume_section', 'general')}`** "
                            f"(Similarity: `{m.get('similarity', 0.0):.3f}`): {m.get('resume_snippet', '')}"
                        )

                with tab_exp3:
                    st.text_area("Extracted Resume Text", cand.resume.raw_text, height=200, disabled=True)

elif not current_jd:
    st.markdown("👉 *Select or upload a Job Description above to evaluate candidates.*")
