import pytest
from pathlib import Path
from ingestion.pdf_parser import PDFParser
from extraction.jd_extractor import JDExtractor
from extraction.resume_extractor import ResumeExtractor
from app.matching.hybrid_ranker import HybridRanker
from app.config import DEFAULT_RANKING_CONFIG, RankingConfig
from app.ui_helpers import (
    SAMPLE_JOB_DESCRIPTIONS,
    get_demo_resume_paths,
    validate_resume_batch,
    generate_leaderboard_csv,
    generate_leaderboard_json,
    format_percentage
)


class TestEndToEndRecruiterPipeline:
    def test_e2e_18_real_resumes_workflow(self):
        """
        Executes the full recruiter workflow on 18 real PDF resumes from data/resumes/
        against the sample Backend Engineer JD.
        """
        # 1. Parse Job Description
        sample_jd_data = SAMPLE_JOB_DESCRIPTIONS["Backend Engineer (Python / Cloud / Microservices)"]
        jd = JDExtractor.parse_jd(sample_jd_data["filename"], sample_jd_data["text"])
        assert "Backend Software Engineer" in jd.title
        assert len(jd.required_skills) > 0
        assert jd.experience_years_required >= 2.0

        # 2. Discover 18 real PDF resumes from data/resumes/
        demo_paths = get_demo_resume_paths(target_count=18)
        assert len(demo_paths) == 18

        # 3. Extract text and validate batch
        raw_items = []
        for p in demo_paths:
            text = PDFParser.extract_text(p)
            raw_items.append((p.name, text))

        validation = validate_resume_batch(raw_items)
        assert validation["total_count"] == 18
        assert validation["count_status"] == "optimal"
        assert validation["valid_count"] == 18, f"Expected all 18 to have extractable text, got: {validation['empty_files']}"

        # 4. Parse into Resume objects
        resumes = [ResumeExtractor.parse_resume(fn, txt) for fn, txt in raw_items]
        assert len(resumes) == 18

        # 5. Execute Hybrid Batch Ranking
        cfg = DEFAULT_RANKING_CONFIG
        ranked_results = HybridRanker.rank_batch(jd, resumes, cfg)
        assert len(ranked_results) == 18

        # 6. Verify sort order (strictly descending by final_score)
        scores = [r.final_score for r in ranked_results]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], f"Ranking not sorted: {scores[i]} < {scores[i+1]}"

        # 7. Verify mathematical diagnostics integrity for every candidate
        for r in ranked_results:
            diag = r.diagnostics
            # Base score identity
            expected_base = round(diag.keyword_contribution + diag.semantic_contribution, 4)
            assert abs(diag.base_score - expected_base) < 1e-4

            # Final score identity
            expected_final = round(max(0.0, min(1.0, diag.base_score - diag.total_penalty)), 4)
            assert abs(r.final_score - expected_final) < 1e-4

            # Provenance and explanation
            assert len(r.ranking_reason) > 20
            assert "Final score:" in r.ranking_reason

        # 8. Verify top 3 spotlight candidates have strong alignment
        top_cand = ranked_results[0]
        assert top_cand.final_score > 0.35, f"Top candidate score unexpectedly low: {top_cand.final_score}"
        assert len(top_cand.matched_skills) > 0

        # 9. Verify CSV and JSON exports generate cleanly
        csv_out = generate_leaderboard_csv(ranked_results)
        assert len(csv_out.splitlines()) == 19  # 1 header + 18 rows
        assert "Rank,Candidate Name,Filename" in csv_out

        json_out = generate_leaderboard_json(ranked_results)
        assert len(json_out) > 500
        assert "final_score_pct" in json_out

    def test_e2e_preset_switching_stability(self):
        """
        Verifies that switching presets from Recommended (0.40/0.60) to Skills-First (0.25/0.75)
        and Strict Compliance (0.60/0.40) maintains deterministic score identities on real resumes.
        """
        sample_jd_data = SAMPLE_JOB_DESCRIPTIONS["Backend Engineer (Python / Cloud / Microservices)"]
        jd = JDExtractor.parse_jd(sample_jd_data["filename"], sample_jd_data["text"])
        demo_paths = get_demo_resume_paths(target_count=5)
        resumes = [ResumeExtractor.parse_resume(p.name, PDFParser.extract_text(p)) for p in demo_paths]

        for preset_name, p in [
            ("Recommended", {"kw": 0.40, "sem": 0.60}),
            ("Skills-First", {"kw": 0.25, "sem": 0.75}),
            ("Strict Compliance", {"kw": 0.60, "sem": 0.40})
        ]:
            cfg = RankingConfig(keyword_weight=p["kw"], semantic_weight=p["sem"])
            results = HybridRanker.rank_batch(jd, resumes, cfg)
            assert len(results) == 5
            for r in results:
                assert r.diagnostics.keyword_weight == p["kw"]
                assert r.diagnostics.semantic_weight == p["sem"]
                assert 0.0 <= r.final_score <= 1.0
