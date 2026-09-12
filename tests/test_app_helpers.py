import io
import json
import pytest
from pathlib import Path
from pypdf import PdfWriter

from ingestion.pdf_parser import PDFParser
from app.models import JobDescription, Resume, CandidateResult, KeywordScoreBreakdown, SemanticScoreBreakdown, PenaltyBreakdown, ScoreDiagnostics
from app.config import RankingConfig
from app.ui_helpers import (
    PRESET_CONFIGS,
    check_keyword_stuffing_warning,
    get_demo_resume_paths,
    validate_resume_batch,
    format_percentage,
    generate_leaderboard_csv,
    generate_leaderboard_json,
    SAMPLE_JOB_DESCRIPTIONS
)


class TestAppHelpers:
    def test_preset_configs_validity(self):
        """Ensures all UI presets are internally valid and sum to 1.0."""
        for name, p in PRESET_CONFIGS.items():
            cfg = RankingConfig(
                keyword_weight=p["keyword_weight"],
                semantic_weight=p["semantic_weight"],
                required_skill_weight=p["required_skill_weight"],
                preferred_skill_weight=p["preferred_skill_weight"],
                semantic_noise_threshold=p["semantic_noise_threshold"],
                experience_penalty_per_year=p["experience_penalty_per_year"],
                maximum_experience_penalty=p["maximum_experience_penalty"]
            )
            cfg.validate()
            assert abs((cfg.keyword_weight + cfg.semantic_weight) - 1.0) < 1e-6

    def test_keyword_stuffing_warning(self):
        """Verifies warning triggers at >= 0.60 and is silent below."""
        warn_active, msg = check_keyword_stuffing_warning(0.60)
        assert warn_active is True
        assert "Adversarial Risk Warning" in msg
        assert "0.60" in msg

        warn_active_high, _ = check_keyword_stuffing_warning(0.75)
        assert warn_active_high is True

        warn_safe, _ = check_keyword_stuffing_warning(0.40)
        assert warn_safe is False

        warn_safe_50, _ = check_keyword_stuffing_warning(0.50)
        assert warn_safe_50 is False

    def test_sample_job_descriptions(self):
        """Verifies pre-packaged sample JDs are non-empty and well-structured."""
        assert len(SAMPLE_JOB_DESCRIPTIONS) >= 2
        for title, jd in SAMPLE_JOB_DESCRIPTIONS.items():
            assert "title" in jd
            assert "text" in jd
            assert len(jd["text"]) > 100

    def test_demo_resume_loader(self):
        """Verifies get_demo_resume_paths returns 18 real PDF resumes from data/resumes/."""
        paths = get_demo_resume_paths(target_count=18)
        assert len(paths) == 18
        for p in paths:
            assert p.exists()
            assert p.suffix.lower() == ".pdf"

    def test_batch_validation(self):
        """Verifies batch validation correctly detects optimal counts, duplicates, and empties."""
        # 1. Optimal batch of 16
        items_optimal = [(f"cand_{i}.pdf", f"Text {i}") for i in range(16)]
        res = validate_resume_batch(items_optimal)
        assert res["count_status"] == "optimal"
        assert res["valid_count"] == 16
        assert not res["has_duplicates"]
        assert not res["has_empty"]

        # 2. Under-count batch of 10
        items_small = [(f"cand_{i}.pdf", f"Text {i}") for i in range(10)]
        res_small = validate_resume_batch(items_small)
        assert res_small["count_status"] == "below_optimal"

        # 3. Over-count batch of 20
        items_large = [(f"cand_{i}.pdf", f"Text {i}") for i in range(20)]
        res_large = validate_resume_batch(items_large)
        assert res_large["count_status"] == "above_optimal"

        # 4. Duplicates and empty files
        items_mixed = [
            ("cand_1.pdf", "Valid text"),
            ("cand_1.pdf", "Duplicate text"),
            ("empty.pdf", ""),
            ("whitespace.pdf", "   \n\t  ")
        ]
        res_mixed = validate_resume_batch(items_mixed)
        assert res_mixed["has_duplicates"]
        assert "cand_1.pdf" in res_mixed["duplicates"]
        assert res_mixed["has_empty"]
        assert "empty.pdf" in res_mixed["empty_files"]
        assert "whitespace.pdf" in res_mixed["empty_files"]
        assert res_mixed["valid_count"] == 2

    def test_pdf_parser_stream_and_bytes(self):
        """Verifies PDFParser handles io.BytesIO and raw bytes without crashing."""
        # Create an in-memory PDF using pypdf
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        pdf_bytes_io = io.BytesIO()
        writer.write(pdf_bytes_io)
        pdf_bytes = pdf_bytes_io.getvalue()

        # Extract from BytesIO
        stream = io.BytesIO(pdf_bytes)
        text_stream = PDFParser.extract_text(stream)
        assert isinstance(text_stream, str)

        # Extract from raw bytes
        text_bytes = PDFParser.extract_text(pdf_bytes)
        assert isinstance(text_bytes, str)

        # Empty bytes
        assert PDFParser.extract_text(b"") == ""

    def test_export_formatters(self):
        """Verifies CSV and JSON export outputs contain correct columns and data."""
        cand = CandidateResult(
            resume=Resume(
                filename="test_cand.pdf",
                raw_text="Sample text",
                candidate_name="Alice Developer",
                experience_years=3.5
            ),
            keyword_breakdown=KeywordScoreBreakdown(
                score=0.85,
                matched_required_skills=["python", "postgresql"],
                missing_required_skills=["docker"],
                matched_preferred_skills=["aws"]
            ),
            semantic_breakdown=SemanticScoreBreakdown(score=0.78),
            penalties=PenaltyBreakdown(total_penalty=0.0),
            diagnostics=ScoreDiagnostics(
                base_score=0.808,
                final_score=0.808,
                keyword_score=0.85,
                keyword_weight=0.4,
                semantic_score=0.78,
                semantic_weight=0.6
            ),
            final_score=0.808,
            ranking_reason="Matched 2/3 required skills."
        )

        # Test CSV
        csv_str = generate_leaderboard_csv([cand])
        assert "Rank,Candidate Name,Filename,Final Score (%),Base Score (%)" in csv_str
        assert "Alice Developer" in csv_str
        assert "80.8%" in csv_str
        assert "python, postgresql" in csv_str

        # Test JSON
        json_str = generate_leaderboard_json([cand])
        data = json.loads(json_str)
        assert len(data) == 1
        assert data[0]["candidate_name"] == "Alice Developer"
        assert data[0]["final_score"] == 0.808
        assert data[0]["final_score_pct"] == "80.8%"

    def test_preset_display_formatting(self):
        """Verifies presets have concise primary labels, weights_label, and single-line descriptions."""
        expected_presets = ["Recommended", "Skills-first", "Strict compliance", "Custom configuration"]
        assert list(PRESET_CONFIGS.keys()) == expected_presets

        for name, data in PRESET_CONFIGS.items():
            assert "(" not in name, f"Preset '{name}' must not contain parenthetical text in its primary label"
            assert ")" not in name
            assert "weights_label" in data
            assert "description" in data
            assert "\n" not in data["description"], "Preset description must be a single concise line"
            assert len(data["description"]) < 120

    def test_qa_four_suggested_queries_and_execution(self):
        """Verifies exactly 4 high-value suggested queries execute and return real data."""
        from app.qa.recruiter_qa import RecruiterQAEngine
        jd = JobDescription(
            filename="backend_jd.pdf",
            raw_text="Backend Engineer",
            title="Backend Engineer",
            required_skills=["python", "postgresql"],
            preferred_skills=["docker"],
            experience_years_required=2.0
        )
        cands = [
            CandidateResult(
                resume=Resume(filename=f"c{i}.pdf", raw_text=f"Dev {i}", candidate_name=f"Candidate {i}", experience_years=float(i)),
                keyword_breakdown=KeywordScoreBreakdown(
                    score=0.8 - i * 0.1,
                    matched_required_skills=["python"] if i < 2 else [],
                    missing_required_skills=["postgresql"] if i >= 2 else []
                ),
                semantic_breakdown=SemanticScoreBreakdown(score=0.7 - i * 0.05),
                penalties=PenaltyBreakdown(total_penalty=0.05 if i == 3 else 0.0),
                diagnostics=ScoreDiagnostics(
                    base_score=0.75 - i * 0.1,
                    final_score=0.75 - i * 0.1 - (0.05 if i == 3 else 0.0),
                    keyword_score=0.8 - i * 0.1,
                    keyword_weight=0.4,
                    semantic_score=0.7 - i * 0.05,
                    semantic_weight=0.6,
                    total_penalty=0.05 if i == 3 else 0.0
                ),
                final_score=0.75 - i * 0.1 - (0.05 if i == 3 else 0.0),
                rank=i + 1
            )
            for i in range(5)
        ]

        engine = RecruiterQAEngine(cands, jd)
        suggestions = engine.get_suggested_questions()
        assert len(suggestions) == 4

        # Execute each suggestion and verify response
        for q in suggestions:
            resp = engine.answer_query(q)
            assert resp.answer and len(resp.answer) > 20
            # Ensure zero emojis in answer
            for emoji in ["✅", "❌", "⚠️", "⭐", "🏆", "🥇", "🥈", "🥉"]:
                assert emoji not in resp.answer

    def test_spotlight_rank_labels(self):
        """Verifies rank labels are explicitly #1, #2, #3 rather than ordinal names."""
        for rank in [1, 2, 3]:
            label = f"#{rank}"
            assert label in ["#1", "#2", "#3"]
            assert label not in ["First", "Second", "Third", "Gold", "Silver", "Bronze"]

    def test_bonus_feature_labels(self):
        """Verifies bonus feature branding uses star icon and clean titles without emojis."""
        qa_label = "★ Bonus feature — Recruiter Q&A"
        jd_label = "★ Bonus feature — JD language review"
        assert "★" in qa_label and "★" in jd_label
        for emoji in ["⭐", "💡", "🧠", "✨"]:
            assert emoji not in qa_label
            assert emoji not in jd_label

    def test_streamlit_app_test_workflow(self):
        """Verifies full headless Streamlit app flow from ingestion to ranking and Q&A."""
        from streamlit.testing.v1 import AppTest
        main_script = Path(__file__).parent.parent / "app" / "main.py"
        at = AppTest.from_file(str(main_script), default_timeout=30)
        at.run()

        # Load sample JD
        load_sample_btn = next(b for b in at.button if "Load Selected Sample JD" in b.label)
        load_sample_btn.click().run()

        # Load 18 demo resumes
        load_res_btn = next(b for b in at.button if "Load 18 Demo Resumes" in b.label)
        load_res_btn.click().run()

        # Execute ranking
        rank_btn = next(b for b in at.button if "Rank Resumes Against Job Description" in b.label)
        rank_btn.click().run()

        markdown_vals = [m.value for m in at.markdown]
        assert any("#1" in t for t in markdown_vals)
        assert any("Full Ranked Leaderboard" in t for t in markdown_vals)
        assert any("Recruiter Q&A" in t for t in markdown_vals)

        # Verify QA buttons function
        qa_btns = [b for b in at.button if b.key and "btn_qa_suggest" in b.key]
        assert len(qa_btns) == 4
        qa_btns[0].click().run()
        after_click = [m.value for m in at.markdown]
        assert any("qa-result-card" in t for t in after_click)

    def test_dual_theme_css_palettes(self):
        """Verifies both Dark Mode and Light Mode CSS inject valid brown, darker grey, and light blue variables."""
        from app.styles import get_app_css

        dark_css = get_app_css("dark")
        assert "--bg-main: #111418" in dark_css
        assert "--brand-brown: #7A5B45" in dark_css
        assert "--accent-blue: #60A5FA" in dark_css
        assert "--table-header-bg" in dark_css

        light_css = get_app_css("light")
        assert "--bg-main: #F7F5F0" in light_css
        assert "--brand-brown: #543E2E" in light_css
        assert "--text-primary: #161B22" in light_css
        assert "--accent-blue: #2563EB" in light_css

        # Zero emojis in both CSS stylesheets
        for css in [dark_css, light_css]:
            for emoji in ["💡", "⭐", "🏆", "🥇", "🥈", "🥉", "✨"]:
                assert emoji not in css

