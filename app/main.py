"""
app/main.py - Smart Candidate Shortlisting Engine
Recruiter Streamlit Application for End-to-End Hybrid Ranking & Explainability.
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
    st.sidebar.markdown("### ⚖️ Calibration & Scoring")

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
        help="Pre-calibrated weight profiles."
    )
    
    st.sidebar.caption(PRESET_CONFIGS[selected_preset]["description"])
    st.sidebar.markdown("---")
    st.sidebar.markdown("#### Weight Allocations")

    kw_slider = st.sidebar.slider(
        "Keyword Match Weight ($W_{\\text{kw}}$)",
        min_value=0.0,
        max_value=1.0,
        value=float(st.session_state.kw_weight),
        step=0.05,
        key="kw_weight",
        help="Relative importance of exact canonical skill matching."
    )

    sem_weight = round(1.0 - kw_slider, 2)
    st.sidebar.info(f"Semantic Match Weight ($W_{{\\text{{sem}}}}$): **{sem_weight:.2f}**")

    has_warning, warning_text = check_keyword_stuffing_warning(kw_slider)
    if has_warning:
        st.sidebar.warning(warning_text)

    with st.sidebar.expander("⚙️ Advanced Calibration Parameters", expanded=False):
        req_weight = st.slider(
            "Required Skill Weight",
            min_value=0.50, max_value=0.90,
            value=float(st.session_state.req_weight), step=0.05,
            key="req_weight",
            help="Weight assigned to mandatory skills relative to preferred skills."
        )
        pref_weight = round(1.0 - req_weight, 2)
        st.caption(f"Preferred Skill Weight: **{pref_weight:.2f}**")

        noise_thresh = st.slider(
            "Semantic Noise Threshold ($\\tau$)",
            min_value=0.05, max_value=0.35,
            value=float(st.session_state.noise_threshold), step=0.01,
            key="noise_threshold",
            help="Cosine similarity floor below which text similarity is mapped to 0.0."
        )
        exp_penalty = st.slider(
            "Experience Penalty Rate (per missing year)",
            min_value=0.01, max_value=0.15,
            value=float(st.session_state.exp_penalty_rate), step=0.01,
            key="exp_penalty_rate",
            help="Deduction per year candidate falls short of required experience."
        )
        exp_cap = st.slider(
            "Maximum Experience Penalty Cap",
            min_value=0.05, max_value=0.40,
            value=float(st.session_state.exp_penalty_cap), step=0.05,
            key="exp_penalty_cap",
            help="Maximum total deduction allowed for experience gaps."
        )

    st.sidebar.markdown("---")
    st.sidebar.markdown("#### System Engine Info")
    st.sidebar.caption("🧠 **Embedding Model**: `all-MiniLM-L6-v2` (Local CPU)")
    st.sidebar.caption("🔒 **Security**: 100% Offline execution, no external API calls")
    st.sidebar.caption("📊 **Benchmark Target**: 15–18 Candidates per JD")

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
    st.markdown("### Step 1: Job Description")
    
    current_jd: Optional[JobDescription] = None
    jd_tab1, jd_tab2, jd_tab3 = st.tabs(["📄 Upload JD (PDF)", "📋 Paste JD Text", "💡 Load Sample JD"])

    with jd_tab1:
        uploaded_jd_pdf = st.file_uploader("Upload Job Description PDF", type=["pdf"], key="jd_pdf_uploader")
        if uploaded_jd_pdf:
            try:
                jd_text = extract_pdf_text_cached(uploaded_jd_pdf.read())
                if jd_text:
                    current_jd = parse_jd_from_text(uploaded_jd_pdf.name, jd_text)
                else:
                    st.error("Could not extract readable text from the uploaded JD PDF.")
            except Exception as e:
                st.error(f"Error parsing uploaded JD PDF: {e}")

    with jd_tab2:
        pasted_jd_text = st.text_area("Paste full Job Description text here:", height=200)
        if st.button("Parse Pasted JD"):
            if pasted_jd_text.strip():
                current_jd = parse_jd_from_text("Pasted_JD.txt", pasted_jd_text)
            else:
                st.warning("Please enter job description text.")

    with jd_tab3:
        sample_name = st.selectbox("Select Demo Job Description:", list(SAMPLE_JOB_DESCRIPTIONS.keys()))
        if st.button("Load Selected Sample JD"):
            sample_data = SAMPLE_JOB_DESCRIPTIONS[sample_name]
            current_jd = parse_jd_from_text(sample_data["filename"], sample_data["text"])

    if current_jd:
        st.success(f"✅ Active Job Description: **{current_jd.title}**")
        with st.expander("📋 Job Description Quality & Bias Check (Pre-Screening Audit)"):
            bias_report = JDBiasDetector.analyze(current_jd)
            st.info(
                "This engine evaluates the structural quality and inclusivity of the JD. "
                "These flags are **informational only** and do not alter candidate scoring."
            )
            if not bias_report.flags:
                st.success(bias_report.summary)
            else:
                st.caption(bias_report.summary)
                for flag in bias_report.flags:
                    st.markdown(f"- **{flag.category}** _(Severity: {flag.severity})_: {flag.rationale}")
                    if flag.source_snippet:
                        st.caption(f"  *Context*: {flag.source_snippet}")

    return current_jd


def render_resume_section() -> List[Any]:
    """Render the resume ingestion UI and return loaded resumes."""
    st.markdown("---")
    st.markdown("### Step 2: Batch Resume Processing")
    
    loaded_resumes = []
    res_tab1, res_tab2 = st.tabs(["⚡ Load 18 Demo Resumes (Benchmark Corpus)", "📁 Upload Custom PDF Batch"])

    with res_tab1:
        st.info("Load the curated 18-resume evaluation batch from `data/resumes/` to test scoring and adversarial defenses.")
        if st.button("⚡ Load 18 Demo Resumes", use_container_width=True):
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
                st.warning("Please upload at least one PDF.")

    if "loaded_resumes" in st.session_state and st.session_state.loaded_resumes:
        loaded_resumes = st.session_state.loaded_resumes
        resume_items = [(r.filename, r.raw_text) for r in loaded_resumes]
        validation_report = validate_resume_batch(resume_items)
        st.success(f"✅ {validation_report['valid_count']} viable candidate resumes parsed and ready.")

        if validation_report["has_empty"]:
            st.warning(f"⚠️ {len(validation_report['empty_files'])} resume(s) yielded no text: {', '.join(validation_report['empty_files'])}")
        if validation_report["has_duplicates"]:
            st.warning(f"⚠️ Duplicate filenames detected: {', '.join(validation_report['duplicates'])}")
                
    return loaded_resumes


def render_top_spotlights(ranked_results: List[CandidateResult]):
    """Render the Top 3 candidate spotlight cards."""
    st.markdown("### 🏆 Top 3 Candidate Spotlight")
    top3 = ranked_results[:3]
    medals = ["🥇 Gold", "🥈 Silver", "🥉 Bronze"]

    cols = st.columns(min(3, len(top3)))
    for i, cand in enumerate(top3):
        with cols[i]:
            st.markdown(f"**{medals[i]}: {cand.resume.candidate_name}**")
            st.markdown(f"### {format_percentage(cand.final_score)}")
            
            st.progress(cand.final_score)
            
            st.markdown("**Core Requirements Met:**")
            matched_req = cand.keyword_breakdown.matched_required_skills
            missing_req = cand.keyword_breakdown.missing_required_skills
            
            st.caption(f"✅ " + (", ".join(matched_req) if matched_req else "None"))
            if missing_req:
                st.caption(f"❌ Missing: " + ", ".join(missing_req))

            with st.expander("📋 Requirement-by-Requirement Evidence Table"):
                evidence = cand.keyword_breakdown.evidence
                req_skills = cand.keyword_breakdown.matched_required_skills + cand.keyword_breakdown.missing_required_skills
                if req_skills:
                    st.table(pd.DataFrame([{
                        "Requirement": req,
                        "Status": "✅ Found" if evidence.get(req, {}).get("status") == "matched" else "❌ Missing",
                        "Source Section": evidence.get(req, {}).get("source_section", "—"),
                        "Evidence Snippet": evidence.get(req, {}).get("source_context", "—")
                    } for req in req_skills]))
                else:
                    st.info("No explicit required skills in JD.")


def render_leaderboard(ranked_results: List[CandidateResult]):
    """Render the full candidate leaderboard."""
    st.markdown("---")
    st.markdown("#### 📊 Full Ranked Leaderboard (All Candidates)")

    search_query = st.text_input("🔍 Search Leaderboard by candidate name or skill", "").strip().lower()

    table_rows = []
    for rank, res in enumerate(ranked_results, 1):
        name = res.resume.candidate_name
        skills_str = ", ".join(res.matched_skills)
        
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
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No candidates match your search query.")

    col1, col2, _ = st.columns([2, 2, 4])
    with col1:
        st.download_button(
            label="📥 Export Leaderboard to CSV",
            data=generate_leaderboard_csv(ranked_results),
            file_name=f"shortlisting_leaderboard_{int(time.time())}.csv",
            mime="text/csv"
        )
    with col2:
        st.download_button(
            label="📥 Export Leaderboard to JSON",
            data=generate_leaderboard_json(ranked_results),
            file_name=f"shortlisting_leaderboard_{int(time.time())}.json",
            mime="application/json"
        )


def render_qa_assistant(ranked_results: List[CandidateResult], current_jd: JobDescription):
    """Render the Recruiter Q&A Engine."""
    st.markdown("---")
    st.markdown("### 💬 Recruiter Q&A Assistant (Evidence-Backed)")
    st.caption("Ask natural-language questions about candidates. Answers are computed deterministically from verified structured evidence — **100% offline**, zero hallucinations.")

    qa_engine = RecruiterQAEngine(ranked_results, current_jd)
    suggested_questions = qa_engine.get_suggested_questions()

    if "active_qa_query" not in st.session_state:
        st.session_state.active_qa_query = ""

    st.markdown("**Suggested Inquiries:**")
    
    if suggested_questions:
        q_cols = st.columns(3)
        for i, q_text in enumerate(suggested_questions[:6]):
            if q_cols[i % 3].button(q_text, use_container_width=True):
                st.session_state.active_qa_query = q_text

    user_query = st.text_input(
        "Or enter your own question:",
        value=st.session_state.active_qa_query,
        placeholder="e.g. Why did #1 rank above #2?",
        key="qa_text_input"
    )

    if user_query:
        qa_resp = qa_engine.answer_query(user_query)
        st.markdown(qa_resp.answer)
        if qa_resp.supporting_evidence:
            with st.expander("🔍 View Verifiable Data Provenance"):
                st.json(qa_resp.supporting_evidence)


def render_deep_dive(ranked_results: List[CandidateResult]):
    """Render the expandable deep dive inspector for each candidate."""
    st.markdown("---")
    st.markdown("#### 🔍 Deep-Dive Candidate Inspector")

    for rank, cand in enumerate(ranked_results, 1):
        title = f"#{rank}: {cand.resume.candidate_name} — Final Score: {format_percentage(cand.final_score)} ({cand.resume.filename})"
        with st.expander(title):
            tab1, tab2, tab3 = st.tabs(["🧠 Decision Provenance", "📊 Score Breakdown", "📄 Extracted Resume Text"])

            with tab1:
                st.markdown("**Ranking Rationale:**")
                st.info(cand.ranking_reason)
                st.write(f"**Experience & Penalty:** {cand.resume.experience_years:.1f} yrs experience | Penalty: {cand.penalties.total_penalty:.4f}")

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
                st.text_area("Raw Text", cand.resume.raw_text, height=200, disabled=True, key=f"raw_{rank}")


def main():
    """Main application entrypoint."""
    st.set_page_config(
        page_title="Smart Candidate Shortlisting Engine",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.markdown("## 📄 Smart Candidate Shortlisting Engine")
    st.markdown("Explainable, local hybrid matching combining explicit skills, contextual semantic embeddings, and calibrated experience penalties.")
    st.info("🔒 **100% Offline Local Engine** — No LLM / API Dependency")

    active_config = render_sidebar()
    current_jd = render_jd_section()
    
    if not current_jd:
        st.markdown("📝 *Select or upload a Job Description above to evaluate candidates.*")
        return

    loaded_resumes = render_resume_section()

    if loaded_resumes and current_jd:
        if st.button("🚀 Rank Resumes Against Job Description", type="primary", use_container_width=True):
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
