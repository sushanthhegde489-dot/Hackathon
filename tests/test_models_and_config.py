import pytest
from app.config import RankingConfig, DEFAULT_RANKING_CONFIG, DEFAULT_KEYWORD_WEIGHT, DEFAULT_SEMANTIC_WEIGHT
from app.models import (
    Resume, CandidateResult, KeywordScoreBreakdown,
    SemanticScoreBreakdown, PenaltyBreakdown, JobDescription, SkillEvidence
)

class TestModelsAndConfig:
    def test_provisional_ranking_config_weights(self):
        config = RankingConfig()
        assert config.keyword_weight == 0.40
        assert config.semantic_weight == 0.60
        assert config.required_skill_weight == 0.70
        assert config.preferred_skill_weight == 0.30

        # Verify global defaults
        assert DEFAULT_RANKING_CONFIG.keyword_weight == 0.40
        assert DEFAULT_RANKING_CONFIG.semantic_weight == 0.60
        assert DEFAULT_KEYWORD_WEIGHT == 0.40
        assert DEFAULT_SEMANTIC_WEIGHT == 0.60

    def test_candidate_result_hierarchical_structure(self):
        resume = Resume(
            filename="candidate1.pdf",
            raw_text="Candidate 1 raw text",
            candidate_name="Alice Smith",
            skills=["react", "nodejs", "mongodb"]
        )

        keyword_breakdown = KeywordScoreBreakdown(
            score=0.85,
            required_skill_score=0.90,
            preferred_skill_score=0.75,
            matched_required_skills=["react", "nodejs"],
            missing_required_skills=["docker"],
            matched_preferred_skills=["mongodb"],
            missing_preferred_skills=["aws"],
            evidence={"react": "Found in Work Experience section", "docker": "Not found in resume"}
        )

        semantic_breakdown = SemanticScoreBreakdown(
            score=0.78,
            strongest_matches=[{"section": "Work Experience", "similarity": 0.82}],
            similarity_evidence={"cosine_sim": 0.78}
        )

        penalties = PenaltyBreakdown(
            experience_penalty=0.05,
            missing_critical_penalty=0.0,
            details={"experience_gap": 0.05},
            total_penalty=0.05
        )

        result = CandidateResult(
            resume=resume,
            keyword_breakdown=keyword_breakdown,
            semantic_breakdown=semantic_breakdown,
            penalties=penalties,
            final_score=0.81,
            ranking_reason="Candidate meets core frontend and backend requirements but lacks Docker experience."
        )

        # Verify property accessors
        assert result.keyword_score == 0.85
        assert result.semantic_score == 0.78
        assert "react" in result.matched_skills
        assert "mongodb" in result.matched_skills
        assert result.missing_skills == ["docker"]
        assert "Candidate meets core" in result.justification

        # Verify dictionary serialization
        d = result.to_dict()
        assert d["candidate_name"] == "Alice Smith"
        assert d["final_score"] == 0.81
        assert d["keyword_score"]["required_skill_score"] == 0.90
        assert d["keyword_score"]["missing_required_skills"] == ["docker"]
        assert d["semantic_score"]["score"] == 0.78
        assert d["penalties"]["total_penalty"] == 0.05
        assert "Docker" in d["ranking_reason"]
