from typing import List, Optional, Dict, Any
from app.config import RankingConfig, DEFAULT_RANKING_CONFIG
from app.models import JobDescription, Resume, CandidateResult
from app.matching.keyword_matcher import KeywordMatcher
from app.matching.semantic_matcher import SemanticMatcher
from app.matching.penalty_calculator import PenaltyCalculator


class HybridRanker:
    """
    Orchestrates the multi-dimensional candidate evaluation pipeline:
    
    1. KeywordMatcher  --> explicit canonical skill alignment (keyword_score)
    2. SemanticMatcher --> contextual & conceptual alignment (semantic_score)
    3. PenaltyCalculator --> experience gap deductions (total_penalty)
    
    Base Score:
      base_score = (keyword_score * keyword_weight) + (semantic_score * semantic_weight)
      
    Final Score:
      final_score = clamp(base_score - total_penalty, 0.0, 1.0)
      
    Guarantees:
    - Candidate Independence: Individual scores are invariant to batch composition.
    - Full Explainability: Every score is auditable through granular breakdown fields
      and human-readable ranking_reason text.
    - Determinism: Stable descending sort with deterministic secondary keys.
    """

    @classmethod
    def _build_ranking_reason(
        cls,
        cand_result: CandidateResult,
        base_score: float,
        cfg: RankingConfig
    ) -> str:
        """Formulates a transparent, human-readable justification for the candidate's ranking."""
        reasons: List[str] = []

        # 1. Keyword summary
        kw = cand_result.keyword_breakdown
        total_req = len(kw.matched_required_skills) + len(kw.missing_required_skills)
        total_pref = len(kw.matched_preferred_skills) + len(kw.missing_preferred_skills)

        if total_req > 0:
            req_msg = f"Matched {len(kw.matched_required_skills)}/{total_req} required skills"
            if kw.matched_required_skills:
                req_msg += f" ({', '.join(kw.matched_required_skills)})"
            if kw.missing_required_skills:
                req_msg += f"; missing: {', '.join(kw.missing_required_skills)}"
            reasons.append(req_msg)
        else:
            reasons.append("No explicit required skills specified in JD")

        if total_pref > 0:
            pref_msg = f"Matched {len(kw.matched_preferred_skills)}/{total_pref} preferred skills"
            if kw.matched_preferred_skills:
                pref_msg += f" ({', '.join(kw.matched_preferred_skills)})"
            reasons.append(pref_msg)

        # 2. Semantic summary
        sem = cand_result.semantic_breakdown
        if sem.strongest_matches:
            top_match = sem.strongest_matches[0]
            reasons.append(
                f"Strongest semantic alignment in {top_match['resume_section']} "
                f"(similarity: {top_match['similarity']:.2f})"
            )

        # 3. Penalty / Experience summary
        pen = cand_result.penalties
        gap = pen.details.get("experience_gap_years", 0.0)
        req_yrs = pen.details.get("required_years", 0.0)
        cand_yrs = pen.details.get("candidate_years", 0.0)

        if req_yrs > 0.0:
            if gap > 0.0:
                reasons.append(
                    f"Experience gap of {gap:.1f} years ({cand_yrs:.1f} vs {req_yrs:.1f} required) "
                    f"incurred a {pen.total_penalty:.4f} penalty"
                )
            else:
                reasons.append(f"Meets experience requirement ({cand_yrs:.1f}/{req_yrs:.1f} years)")
        else:
            reasons.append("No formal experience requirement")

        # 4. Final calculation formula
        reasons.append(
            f"Final score: {cand_result.final_score:.4f} "
            f"(Base: {base_score:.4f} [KW: {kw.score:.4f} × {cfg.keyword_weight:.2f} + "
            f"Sem: {sem.score:.4f} × {cfg.semantic_weight:.2f}] - Penalty: {pen.total_penalty:.4f})"
        )

        return ". ".join(reasons)

    @classmethod
    def rank(
        cls,
        jd: JobDescription,
        resume: Resume,
        config: Optional[RankingConfig] = None
    ) -> CandidateResult:
        """
        Evaluates a single Candidate Resume against a Job Description.
        Returns a fully populated, explainable CandidateResult.
        """
        cfg = config or DEFAULT_RANKING_CONFIG
        cfg.validate()

        # 1. Evaluate explicit keyword matching
        kw_res = KeywordMatcher.match(jd, resume, cfg)

        # 2. Evaluate semantic matching
        sem_res = SemanticMatcher.match(
            jd,
            resume,
            cfg,
            noise_threshold=cfg.semantic_noise_threshold
        )

        # 3. Calculate penalties
        penalties = PenaltyCalculator.calculate(jd, resume, cfg)

        # 4. Compute composite hybrid score
        base_score = (
            (kw_res.keyword_score * cfg.keyword_weight) +
            (sem_res.semantic_score * cfg.semantic_weight)
        )
        final_score = round(max(0.0, min(1.0, base_score - penalties.total_penalty)), 4)

        # 5. Assemble result object
        result = CandidateResult(
            resume=resume,
            keyword_breakdown=kw_res.keyword_breakdown,
            semantic_breakdown=sem_res.semantic_breakdown,
            penalties=penalties,
            final_score=final_score,
            ranking_reason=""
        )

        # 6. Formulate comprehensive ranking explanation
        result.ranking_reason = cls._build_ranking_reason(result, base_score, cfg)
        return result

    @classmethod
    def rank_batch(
        cls,
        jd: JobDescription,
        resumes: List[Resume],
        config: Optional[RankingConfig] = None
    ) -> List[CandidateResult]:
        """
        Evaluates and ranks a batch of Candidate Resumes against a Job Description.
        Optimized for batch performance: performs batched text encoding for semantic matching.
        Returns CandidateResults sorted descending by final_score with deterministic tie-breaking.
        """
        if not resumes:
            return []

        cfg = config or DEFAULT_RANKING_CONFIG
        cfg.validate()

        # 1. Batch semantic evaluation (encodes all candidate chunks in single passes)
        sem_results = SemanticMatcher.match_batch(
            jd,
            resumes,
            cfg,
            noise_threshold=cfg.semantic_noise_threshold
        )
        sem_by_filename = {r.resume.filename: r.semantic_breakdown for r in sem_results}

        # 2. Evaluate keyword matching and penalties per candidate
        results: List[CandidateResult] = []
        for resume in resumes:
            kw_res = KeywordMatcher.match(jd, resume, cfg)
            sem_breakdown = sem_by_filename.get(resume.filename)
            penalties = PenaltyCalculator.calculate(jd, resume, cfg)

            kw_score = kw_res.keyword_score
            sem_score = sem_breakdown.score if sem_breakdown else 0.0

            base_score = (kw_score * cfg.keyword_weight) + (sem_score * cfg.semantic_weight)
            final_score = round(max(0.0, min(1.0, base_score - penalties.total_penalty)), 4)

            cand_res = CandidateResult(
                resume=resume,
                keyword_breakdown=kw_res.keyword_breakdown,
                semantic_breakdown=sem_breakdown,
                penalties=penalties,
                final_score=final_score,
                ranking_reason=""
            )
            cand_res.ranking_reason = cls._build_ranking_reason(cand_res, base_score, cfg)
            results.append(cand_res)

        # 3. Deterministic descending sort: primary by final_score, secondary by filename, tertiary by candidate_name
        results.sort(key=lambda r: (-r.final_score, r.resume.filename, r.resume.candidate_name))
        return results
