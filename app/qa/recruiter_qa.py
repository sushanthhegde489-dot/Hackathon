"""
app/qa/recruiter_qa.py - Deterministic, Evidence-Backed Recruiter Q&A Engine.

Provides transparent natural-language answers to recruiter questions about candidates,
rankings, skill mismatches, score compositions, and experience deductions.
Operates 100% offline without external API keys or LLM hallucinations:
answers are synthesized directly from verified structured candidate provenance.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

from app.models import CandidateResult, JobDescription
from extraction.skill_normalizer import SkillNormalizer
from extraction.jd_extractor import JDExtractor
from app.ui_helpers import format_percentage


@dataclass
class QAResponse:
    """Structured response to a recruiter query with provenance evidence."""
    query: str
    intent: str
    answer: str
    candidates_involved: List[str] = field(default_factory=list)
    supporting_evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "intent": self.intent,
            "answer": self.answer,
            "candidates_involved": self.candidates_involved,
            "supporting_evidence": self.supporting_evidence
        }


class RecruiterQAEngine:
    """
    Interprets recruiter queries and formulates mathematically verifiable,
    evidence-backed explanations directly from CandidateResults and JobDescription.
    """

    def __init__(self, results: List[CandidateResult], jd: JobDescription):
        self.results = results
        self.jd = jd
        # Map by lowercase name, filename, and rank for quick resolution
        self.by_name: Dict[str, CandidateResult] = {}
        self.by_filename: Dict[str, CandidateResult] = {}
        self.by_rank: Dict[int, CandidateResult] = {}

        for idx, r in enumerate(results, 1):
            # Ensure rank is set
            r.rank = idx
            name_lower = r.resume.candidate_name.lower().strip()
            self.by_name[name_lower] = r
            self.by_filename[r.resume.filename.lower()] = r
            self.by_rank[idx] = r

    def find_candidate(self, identifier: str) -> Optional[CandidateResult]:
        """
        Resolves a candidate by rank (#1, rank 1), name, or filename.
        Case-insensitive and substring tolerant.
        """
        id_str = identifier.strip().lower()
        if not id_str:
            return None

        # 1. Check rank pattern: #1, rank 1, rank #1, 1st, 2nd, 3rd, top 1
        rank_match = re.search(r"(?:rank\s*#?|#)(\d+)", id_str)
        if rank_match:
            rank_num = int(rank_match.group(1))
            if rank_num in self.by_rank:
                return self.by_rank[rank_num]

        # 2. Check ordinal keywords
        if "first" in id_str or "1st" in id_str or "winner" in id_str:
            return self.by_rank.get(1)
        if "second" in id_str or "2nd" in id_str or "runner up" in id_str:
            return self.by_rank.get(2)
        if "third" in id_str or "3rd" in id_str:
            return self.by_rank.get(3)

        # 3. Exact name or filename match
        if id_str in self.by_name:
            return self.by_name[id_str]
        if id_str in self.by_filename:
            return self.by_filename[id_str]

        # 4. Partial substring match against candidate names
        for name, cand in self.by_name.items():
            if id_str in name or name in id_str:
                return cand

        # 5. Partial match against filenames
        for fn, cand in self.by_filename.items():
            if id_str in fn:
                return cand

        return None

    def get_suggested_questions(self) -> List[str]:
        """Returns 6 curated example questions relevant to the current shortlist."""
        if not self.results:
            return []

        c1 = self.results[0]
        c2 = self.results[1] if len(self.results) > 1 else None
        c4 = self.results[3] if len(self.results) > 3 else None

        questions = []
        if c1 and c2:
            questions.append(f"Why did {c1.resume.candidate_name} rank above {c2.resume.candidate_name}?")
        if c4:
            questions.append(f"Why is {c4.resume.candidate_name} not in the top 3?")

        # Check required skills for specific query
        if self.jd.required_skills:
            target_skill = self.jd.required_skills[0].title()
            questions.append(f"Which candidates are missing {target_skill}?")

        questions.append("Which candidates have no experience penalty?")
        questions.append("Who has strong semantic alignment despite missing some keywords?")
        questions.append("Show candidates who match required skills but lack preferred skills.")

        return questions

    def answer_query(self, query: str) -> QAResponse:
        """
        Main entry point: classifies recruiter intent and routes to evidence-backed generator.
        """
        q = query.strip()
        q_lower = q.lower()

        # 1. Comparative: "Why did X rank above Y?" or "Compare X and Y"
        if any(w in q_lower for w in ["rank above", "ranked above", "higher than", "better than", "beat", "vs", "versus", "compare"]):
            return self._handle_comparison(q)

        # 2. Exclusion / Rank Why: "Why is X not in top 3?" or "Why did X rank #N?"
        if any(w in q_lower for w in ["not in the top 3", "not in top 3", "why is", "why did"]) and any(w in q_lower for w in ["rank", "score", "top"]):
            # Check if this is a single candidate query
            return self._handle_why_ranked(q)

        # 3. Penalty questions: "Why did X lose points?" or "What penalties were applied?"
        if any(w in q_lower for w in ["lose points", "lost points", "penalty", "penalties", "deduction", "deducted"]):
            if any(w in q_lower for w in ["no penalty", "zero penalty", "without penalty", "no experience penalty"]):
                return self._handle_no_penalty(q)
            return self._handle_penalty_reasons(q)

        # 4. Semantic Queries: "Who has the strongest semantic match?" or "paraphrase"
        if any(w in q_lower for w in ["semantic", "meaning", "concept", "paraphrase", "transferable"]):
            if any(w in q_lower for w in ["despite", "weak keyword", "missing keyword", "without keyword"]):
                return self._handle_paraphrase_standouts(q)
            return self._handle_semantic_standouts(q)

        # 5. Skill Questions: "Which candidates are missing X?" or "Who has X?"
        if any(w in q_lower for w in ["missing", "lacks", "lack", "without"]):
            return self._handle_missing_skill(q)

        if any(w in q_lower for w in ["who has", "which candidates have", "candidates with", "possess"]):
            return self._handle_has_skill(q)

        if "preferred" in q_lower and "required" in q_lower:
            return self._handle_required_without_preferred(q)

        # 6. Fallback: Check if user named a candidate
        candidate = self._extract_first_candidate_from_text(q_lower)
        if candidate:
            return self._handle_candidate_profile_summary(q, candidate)

        # Default summary
        return self._handle_top_summary(q)

    # -------------------------------------------------------------------------
    # INTENT HANDLERS
    # -------------------------------------------------------------------------

    def _extract_two_candidates(self, query: str) -> Tuple[Optional[CandidateResult], Optional[CandidateResult]]:
        """Extracts two candidate references from comparison query."""
        # Try splitting by 'above', 'than', 'vs', 'versus', 'and'
        separators = ["ranked above", "rank above", "higher than", "better than", "versus", " vs ", " and "]
        for sep in separators:
            if sep in query.lower():
                parts = query.lower().split(sep, 1)
                c1 = self._extract_first_candidate_from_text(parts[0])
                c2 = self._extract_first_candidate_from_text(parts[1])
                if c1 and c2 and c1.resume.filename != c2.resume.filename:
                    return c1, c2

        # Alternatively, find all candidates mentioned in query
        found = []
        for cand in self.results:
            name_parts = cand.resume.candidate_name.lower().split()
            first_name = name_parts[0] if name_parts else ""
            if (cand.resume.candidate_name.lower() in query.lower() or 
                (len(first_name) > 3 and first_name in query.lower()) or
                f"#{cand.rank}" in query.lower() or
                f"rank {cand.rank}" in query.lower()):
                if cand not in found:
                    found.append(cand)
            if len(found) == 2:
                break

        if len(found) == 2:
            return found[0], found[1]

        # Default to #1 and #2 if comparing top candidates
        if len(self.results) >= 2:
            return self.results[0], self.results[1]
        return None, None

    def _extract_first_candidate_from_text(self, text: str) -> Optional[CandidateResult]:
        """Extracts the first matching candidate from text snippet."""
        # Check rank patterns (#1, #2, rank 1, etc.)
        rank_match = re.search(r"(?:rank\s*#?|#)(\d+)", text)
        if rank_match:
            r_num = int(rank_match.group(1))
            if r_num in self.by_rank:
                return self.by_rank[r_num]

        # Check candidate names
        text_lower = text.lower()
        for cand in self.results:
            full_name = cand.resume.candidate_name.lower()
            if full_name in text_lower:
                return cand
            # First name check (at least 4 chars to avoid false positives)
            first_name = full_name.split()[0] if full_name.split() else ""
            if len(first_name) >= 4 and f" {first_name} " in f" {text_lower} ":
                return cand

        return None

    def _handle_comparison(self, query: str) -> QAResponse:
        """Formulates an exact mathematical and skill-level comparison between two candidates."""
        c1, c2 = self._extract_two_candidates(query)
        if not c1 or not c2:
            return QAResponse(
                query=query,
                intent="comparison",
                answer="Could not clearly identify the two candidates to compare. Please specify candidate names or ranks (e.g. 'Why did #1 rank above #2?')."
            )

        # Ensure c_higher is the higher-ranked candidate
        c_higher, c_lower = (c1, c2) if c1.final_score >= c2.final_score else (c2, c1)

        d_hi = c_higher.diagnostics
        d_lo = c_lower.diagnostics
        kw_hi = c_higher.keyword_breakdown
        kw_lo = c_lower.keyword_breakdown
        pen_hi = c_higher.penalties
        pen_lo = c_lower.penalties

        score_diff = c_higher.final_score - c_lower.final_score
        kw_contrib_diff = d_hi.keyword_contribution - d_lo.keyword_contribution
        sem_contrib_diff = d_hi.semantic_contribution - d_lo.semantic_contribution
        penalty_diff = pen_lo.total_penalty - pen_hi.total_penalty

        # Skills analysis
        unique_req_hi = set(kw_hi.matched_required_skills) - set(kw_lo.matched_required_skills)
        unique_pref_hi = set(kw_hi.matched_preferred_skills) - set(kw_lo.matched_preferred_skills)
        missing_lo_not_hi = set(kw_lo.missing_required_skills) - set(kw_hi.missing_required_skills)

        # Build natural language rationale
        reasons = []

        # 1. Semantic contribution
        if sem_contrib_diff > 0.02:
            reasons.append(
                f"**Higher Semantic Alignment**: {c_higher.resume.candidate_name} scored "
                f"{d_hi.semantic_score:.2f} (contributing +{d_hi.semantic_contribution:.3f}) vs "
                f"{d_lo.semantic_score:.2f} (+{d_lo.semantic_contribution:.3f}) for {c_lower.resume.candidate_name} "
                f"(a net +{sem_contrib_diff:.3f} advantage)."
            )
        elif sem_contrib_diff < -0.02:
            reasons.append(
                f"**Semantic Alignment**: Although {c_lower.resume.candidate_name} had a slight semantic advantage "
                f"({d_lo.semantic_score:.2f} vs {d_hi.semantic_score:.2f}), it was outweighed by skill matching."
            )

        # 2. Keyword & Required skill coverage
        if len(unique_req_hi) > 0:
            skills_str = ", ".join(sorted(list(unique_req_hi)))
            reasons.append(
                f"**Critical Required Skills**: {c_higher.resume.candidate_name} satisfied required skill(s) that "
                f"{c_lower.resume.candidate_name} lacked ({skills_str}), giving a keyword contribution advantage "
                f"of +{kw_contrib_diff:.3f} ({d_hi.keyword_score:.2f} vs {d_lo.keyword_score:.2f})."
            )
        elif kw_contrib_diff > 0.01:
            reasons.append(
                f"**Skill Coverage**: {c_higher.resume.candidate_name} had broader technical skill alignment "
                f"({d_hi.keyword_score:.2f} vs {d_lo.keyword_score:.2f}, +{kw_contrib_diff:.3f} contribution)."
            )

        # 3. Experience penalty
        if penalty_diff > 0.01:
            gap_lo = pen_lo.details.get("experience_gap_years", 0.0)
            reasons.append(
                f"**Experience Deduction**: {c_lower.resume.candidate_name} incurred an experience penalty of "
                f"-{pen_lo.total_penalty:.3f} (due to a {gap_lo:.1f}-year experience gap), whereas "
                f"{c_higher.resume.candidate_name} incurred {pen_hi.total_penalty:.3f} penalty."
            )

        if not reasons:
            reasons.append(
                f"Both candidates had closely comparable profiles, with {c_higher.resume.candidate_name} edging out "
                f"by {score_diff:.4f} in final score."
            )

        answer = (
            f"### Comparison: **{c_higher.resume.candidate_name}** (Rank #{c_higher.rank}, {format_percentage(c_higher.final_score)}) "
            f"vs **{c_lower.resume.candidate_name}** (Rank #{c_lower.rank}, {format_percentage(c_lower.final_score)})\n\n"
            f"{c_higher.resume.candidate_name} ranked above {c_lower.resume.candidate_name} by a margin of "
            f"**{format_percentage(score_diff)}** ({c_higher.final_score:.4f} vs {c_lower.final_score:.4f}).\n\n"
            f"**Key Factors:**\n- " + "\n- ".join(reasons)
        )

        return QAResponse(
            query=query,
            intent="comparison",
            answer=answer,
            candidates_involved=[c_higher.resume.candidate_name, c_lower.resume.candidate_name],
            supporting_evidence={
                "score_difference": round(score_diff, 4),
                "higher_candidate": c_higher.to_dict(),
                "lower_candidate": c_lower.to_dict()
            }
        )

    def _handle_why_ranked(self, query: str) -> QAResponse:
        """Explains why a candidate did not reach the top 3 or ranked at a specific position."""
        candidate = self._extract_first_candidate_from_text(query)
        if not candidate:
            # If no candidate specified, default to #4 candidate
            candidate = self.results[3] if len(self.results) > 3 else (self.results[-1] if self.results else None)

        if not candidate:
            return QAResponse(query=query, intent="rank_why", answer="No candidate results available to explain.")

        # If candidate is already in top 3
        if candidate.rank <= 3:
            return QAResponse(
                query=query,
                intent="rank_why",
                answer=(
                    f"**{candidate.resume.candidate_name}** is already in the top 3 (Rank #{candidate.rank}) "
                    f"with a final score of **{format_percentage(candidate.final_score)}**!\n\n"
                    f"**Rationale:** {candidate.ranking_reason}"
                ),
                candidates_involved=[candidate.resume.candidate_name]
            )

        # Compare with the #3 threshold candidate
        threshold_cand = self.results[2] if len(self.results) >= 3 else None
        gap_to_top3 = (threshold_cand.final_score - candidate.final_score) if threshold_cand else 0.0

        deficiencies = []
        kw = candidate.keyword_breakdown
        pen = candidate.penalties

        if kw.missing_required_skills:
            deficiencies.append(
                f"Missing critical required skill(s): **{', '.join(kw.missing_required_skills)}** "
                f"(Required skill score was {kw.required_skill_score:.2f})"
            )

        if pen.total_penalty > 0.0:
            gap_yrs = pen.details.get("experience_gap_years", 0.0)
            deficiencies.append(
                f"Incurred an experience deduction of **-{pen.total_penalty:.3f}** "
                f"({gap_yrs:.1f} years below the {self.jd.experience_years_required:.1f}-year requirement)"
            )

        if candidate.semantic_breakdown.score < 0.45:
            deficiencies.append(
                f"Lower semantic alignment with core responsibilities: **{candidate.semantic_breakdown.score:.2f}** "
                f"(top candidates averaged >0.65)"
            )

        if not deficiencies:
            deficiencies.append("Marginally lower composite score across both keyword and semantic alignment.")

        answer = (
            f"### Why is **{candidate.resume.candidate_name}** (Rank #{candidate.rank}) not in the Top 3?\n\n"
            f"**{candidate.resume.candidate_name}** achieved a score of **{format_percentage(candidate.final_score)}**, "
            f"falling **{format_percentage(gap_to_top3)}** short of the #3 cutoff "
            f"({threshold_cand.resume.candidate_name if threshold_cand else 'Top 3'} at {format_percentage(threshold_cand.final_score if threshold_cand else 0.0)}).\n\n"
            f"**Primary Limiting Factors:**\n- " + "\n- ".join(deficiencies) + "\n\n"
            f"**Formula Breakdown:** Base: {candidate.diagnostics.base_score:.4f} "
            f"[KW: {candidate.diagnostics.keyword_score:.2f} × {candidate.diagnostics.keyword_weight:.2f} + "
            f"Sem: {candidate.diagnostics.semantic_score:.2f} × {candidate.diagnostics.semantic_weight:.2f}] "
            f"- Penalty: {pen.total_penalty:.4f} = {candidate.final_score:.4f}"
        )

        return QAResponse(
            query=query,
            intent="rank_why",
            answer=answer,
            candidates_involved=[candidate.resume.candidate_name],
            supporting_evidence={"candidate": candidate.to_dict(), "gap_to_top3": round(gap_to_top3, 4)}
        )

    def _handle_missing_skill(self, query: str) -> QAResponse:
        """Identifies which candidates are missing a specified skill."""
        # Find skill name mentioned in query
        target_skill = None
        for skill in self.jd.all_skills() + SkillNormalizer.TECH_SKILLS_VOCAB:
            if re.search(r"\b" + re.escape(skill) + r"\b", query, re.IGNORECASE):
                target_skill = SkillNormalizer.normalize(skill)
                break

        if not target_skill:
            # If no explicit skill mentioned, show candidates missing any required skill
            missing_any = [
                c for c in self.results if c.keyword_breakdown.missing_required_skills
            ]
            cand_bullets = [
                f"- **{c.resume.candidate_name}** (Rank #{c.rank}): missing {', '.join(c.keyword_breakdown.missing_required_skills)}"
                for c in missing_any[:8]
            ]
            return QAResponse(
                query=query,
                intent="missing_skill",
                answer=(
                    f"### Candidates Missing Required Skills ({len(missing_any)}/{len(self.results)} total)\n\n"
                    + "\n".join(cand_bullets)
                ),
                candidates_involved=[c.resume.candidate_name for c in missing_any]
            )

        # Check who is missing this specific normalized skill
        missing_cands = []
        has_cands = []
        for c in self.results:
            kw = c.keyword_breakdown
            if target_skill in kw.missing_required_skills or target_skill in kw.missing_preferred_skills:
                missing_cands.append(c)
            elif target_skill in kw.matched_required_skills or target_skill in kw.matched_preferred_skills:
                has_cands.append(c)
            else:
                # Skill was not explicitly in required or preferred
                if target_skill not in c.resume.skills:
                    missing_cands.append(c)
                else:
                    has_cands.append(c)

        answer = (
            f"### Skill Audit: **{target_skill.title()}**\n\n"
            f"- **Missing {target_skill.title()}** ({len(missing_cands)} candidates): "
            f"{', '.join([f'{c.resume.candidate_name} (#{c.rank})' for c in missing_cands[:8]]) or 'None'}\n"
            f"- **Verified with {target_skill.title()}** ({len(has_cands)} candidates): "
            f"{', '.join([f'{c.resume.candidate_name} (#{c.rank})' for c in has_cands[:8]]) or 'None'}"
        )

        return QAResponse(
            query=query,
            intent="missing_skill",
            answer=answer,
            candidates_involved=[c.resume.candidate_name for c in missing_cands],
            supporting_evidence={"skill": target_skill, "missing_count": len(missing_cands)}
        )

    def _handle_has_skill(self, query: str) -> QAResponse:
        """Finds candidates possessing a specific skill."""
        target_skill = None
        for skill in self.jd.all_skills() + SkillNormalizer.TECH_SKILLS_VOCAB:
            if re.search(r"\b" + re.escape(skill) + r"\b", query, re.IGNORECASE):
                target_skill = SkillNormalizer.normalize(skill)
                break

        if not target_skill:
            return QAResponse(
                query=query,
                intent="has_skill",
                answer="Please specify a technical skill to search for (e.g. 'Who has Python?' or 'Who has Docker?')."
            )

        matching_cands = []
        for c in self.results:
            if (target_skill in c.keyword_breakdown.matched_required_skills or 
                target_skill in c.keyword_breakdown.matched_preferred_skills or
                target_skill in c.resume.skills):
                matching_cands.append(c)

        if matching_cands:
            cand_list = [f"**{c.resume.candidate_name}** (Rank #{c.rank}, Score: {format_percentage(c.final_score)})" for c in matching_cands]
            answer = (
                f"### Candidates with **{target_skill.title()}** ({len(matching_cands)} found):\n\n- "
                + "\n- ".join(cand_list)
            )
        else:
            answer = f"No evaluated candidates matched the skill **{target_skill.title()}**."

        return QAResponse(
            query=query,
            intent="has_skill",
            answer=answer,
            candidates_involved=[c.resume.candidate_name for c in matching_cands]
        )

    def _handle_required_without_preferred(self, query: str) -> QAResponse:
        """Finds candidates matching required skills but missing preferred bonus skills."""
        cands = []
        for c in self.results:
            kw = c.keyword_breakdown
            req_matched = len(kw.matched_required_skills)
            req_missing = len(kw.missing_required_skills)
            pref_matched = len(kw.matched_preferred_skills)

            # High required skill coverage, low preferred
            if req_matched > 0 and req_missing == 0 and pref_matched == 0:
                cands.append(c)

        if not cands:
            # Relax to more required than preferred
            cands = [c for c in self.results if len(c.keyword_breakdown.matched_required_skills) >= 2 and len(c.keyword_breakdown.matched_preferred_skills) == 0]

        if cands:
            bullets = [
                f"- **{c.resume.candidate_name}** (Rank #{c.rank}, {format_percentage(c.final_score)}): "
                f"Matched required ({', '.join(c.keyword_breakdown.matched_required_skills)}); "
                f"zero preferred skills matched."
                for c in cands[:6]
            ]
            answer = (
                f"### Candidates Satisfying Core Requirements but Lacking Preferred Skills ({len(cands)} candidates):\n\n"
                + "\n".join(bullets)
            )
        else:
            answer = "All candidates with strong required skill matches also possessed at least one preferred skill."

        return QAResponse(
            query=query,
            intent="required_without_preferred",
            answer=answer,
            candidates_involved=[c.resume.candidate_name for c in cands]
        )

    def _handle_no_penalty(self, query: str) -> QAResponse:
        """Lists candidates who incurred zero experience deductions."""
        clean_cands = [c for c in self.results if c.penalties.total_penalty == 0.0]
        bullets = [
            f"- **{c.resume.candidate_name}** (Rank #{c.rank}): {c.resume.experience_years:.1f} yrs experience "
            f"(required: {self.jd.experience_years_required:.1f} yrs)"
            for c in clean_cands
        ]

        answer = (
            f"### Candidates with Zero Experience Penalty ({len(clean_cands)}/{len(self.results)} total)\n\n"
            f"These candidates fully satisfied the **{self.jd.experience_years_required:.1f}-year** experience requirement:\n\n"
            + "\n".join(bullets)
        )

        return QAResponse(
            query=query,
            intent="no_penalty",
            answer=answer,
            candidates_involved=[c.resume.candidate_name for c in clean_cands]
        )

    def _handle_penalty_reasons(self, query: str) -> QAResponse:
        """Explains why a candidate or candidates incurred deductions."""
        candidate = self._extract_first_candidate_from_text(query)
        if candidate:
            pen = candidate.penalties
            if pen.total_penalty == 0.0:
                return QAResponse(
                    query=query,
                    intent="penalty_reasons",
                    answer=f"**{candidate.resume.candidate_name}** incurred **no penalties** (0.0)! They meet or exceed the required experience.",
                    candidates_involved=[candidate.resume.candidate_name]
                )

            gap = pen.details.get("experience_gap_years", 0.0)
            answer = (
                f"### Deduction Details for **{candidate.resume.candidate_name}**\n\n"
                f"- **Total Penalty Applied**: `-{pen.total_penalty:.4f}`\n"
                f"- **Experience Gap**: {gap:.1f} years ({candidate.resume.experience_years:.1f} yrs possessed vs {self.jd.experience_years_required:.1f} yrs required)\n"
                f"- **Penalty Rate**: 5% per missing year (capped at 20% max)\n"
                f"- **Impact on Ranking**: Reduced base score from {candidate.diagnostics.base_score:.4f} to final score {candidate.final_score:.4f}."
            )
            return QAResponse(query=query, intent="penalty_reasons", answer=answer, candidates_involved=[candidate.resume.candidate_name])

        # Overview of all penalized candidates
        penalized = [c for c in self.results if c.penalties.total_penalty > 0.0]
        bullets = [
            f"- **{c.resume.candidate_name}** (#{c.rank}): -{c.penalties.total_penalty:.3f} penalty "
            f"({c.resume.experience_years:.1f} vs {self.jd.experience_years_required:.1f} yrs required)"
            for c in penalized[:8]
        ]
        answer = (
            f"### Overview: Candidates with Experience Deductions ({len(penalized)} candidates)\n\n"
            + "\n".join(bullets)
        )
        return QAResponse(query=query, intent="penalty_reasons", answer=answer)

    def _handle_semantic_standouts(self, query: str) -> QAResponse:
        """Highlights candidates with the strongest semantic alignment."""
        by_sem = sorted(self.results, key=lambda c: -c.semantic_breakdown.score)
        bullets = []
        for c in by_sem[:4]:
            sem = c.semantic_breakdown
            top_snippet = sem.strongest_matches[0].get("resume_snippet", "")[:120] if sem.strongest_matches else ""
            bullets.append(
                f"- **{c.resume.candidate_name}** (Rank #{c.rank}) — Semantic Score: **{format_percentage(sem.score)}**\n"
                f"  *Evidence:* \"{top_snippet}...\""
            )

        answer = (
            "### Top Candidates by Semantic Context Alignment\n\n"
            + "\n".join(bullets)
        )
        return QAResponse(query=query, intent="semantic_standouts", answer=answer)

    def _handle_paraphrase_standouts(self, query: str) -> QAResponse:
        """Finds candidates with high semantic alignment despite lower keyword matches (paraphrased knowledge)."""
        paraphrasers = [
            c for c in self.results if (c.semantic_breakdown.score - c.keyword_breakdown.score) >= 0.10
        ]
        paraphrasers.sort(key=lambda c: -(c.semantic_breakdown.score - c.keyword_breakdown.score))

        if paraphrasers:
            bullets = []
            for c in paraphrasers[:4]:
                diff = c.semantic_breakdown.score - c.keyword_breakdown.score
                bullets.append(
                    f"- **{c.resume.candidate_name}** (Rank #{c.rank}): Semantic **{format_percentage(c.semantic_breakdown.score)}** "
                    f"vs Keyword **{format_percentage(c.keyword_breakdown.score)}** (+{format_percentage(diff)} semantic delta)."
                )
            answer = (
                f"### Transferable Knowledge & Paraphrase Standouts ({len(paraphrasers)} found)\n\n"
                f"These candidates demonstrate strong contextual and architectural alignment with the role "
                f"despite not repeating all literal tech keywords:\n\n"
                + "\n".join(bullets)
            )
        else:
            answer = "No significant divergence observed between keyword and semantic scores across this batch."

        return QAResponse(query=query, intent="paraphrase_standouts", answer=answer)

    def _handle_candidate_profile_summary(self, query: str, cand: CandidateResult) -> QAResponse:
        """Returns a comprehensive summary for a single candidate."""
        diag = cand.diagnostics
        kw = cand.keyword_breakdown
        pen = cand.penalties

        answer = (
            f"### Profile Summary: **{cand.resume.candidate_name}** (Rank #{cand.rank})\n\n"
            f"- **Final Score**: **{format_percentage(cand.final_score)}** (Base: {format_percentage(diag.base_score)})\n"
            f"- **Keyword Match**: {format_percentage(diag.keyword_score)} (Matched {len(kw.matched_required_skills)} required, {len(kw.matched_preferred_skills)} preferred)\n"
            f"- **Semantic Match**: {format_percentage(diag.semantic_score)} (Contribution: +{diag.semantic_contribution:.3f})\n"
            f"- **Experience**: {cand.resume.experience_years:.1f} years (Penalty: {pen.total_penalty:.4f})\n\n"
            f"**Ranking Rationale:** {cand.ranking_reason}"
        )
        return QAResponse(query=query, intent="profile_summary", answer=answer, candidates_involved=[cand.resume.candidate_name])

    def _handle_top_summary(self, query: str) -> QAResponse:
        """Returns a general shortlist summary of the top 3 candidates."""
        if not self.results:
            return QAResponse(query=query, intent="summary", answer="No candidate results available.")

        top3 = self.results[:3]
        bullets = [
            f"1. **{c.resume.candidate_name}** (Score: **{format_percentage(c.final_score)}**): "
            f"Matched {len(c.keyword_breakdown.matched_required_skills)} required skills; "
            f"Semantic: {format_percentage(c.semantic_breakdown.score)}."
            for c in top3
        ]

        answer = (
            f"### Shortlisting Summary for **{self.jd.title}**\n\n"
            f"Evaluated **{len(self.results)} candidates** against **{len(self.jd.required_skills)} required** "
            f"and **{len(self.jd.preferred_skills)} preferred** skills.\n\n"
            f"**Top 3 Shortlist:**\n" + "\n".join(bullets)
        )
        return QAResponse(query=query, intent="summary", answer=answer, candidates_involved=[c.resume.candidate_name for c in top3])
