import re
import os
import warnings
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple, Union
import numpy as np

# Suppress HuggingFace / tokenizers noise
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning)

from app.config import RankingConfig, DEFAULT_RANKING_CONFIG, DEFAULT_EMBEDDING_MODEL
from app.models import (
    JobDescription, Resume, CandidateResult, SemanticScoreBreakdown,
    KeywordScoreBreakdown, PenaltyBreakdown
)
from extraction.jd_extractor import JDExtractor
from extraction.resume_extractor import ResumeExtractor
from ingestion.text_cleaner import TextCleaner


@dataclass
class TextChunk:
    """Represents a section-aware semantic text snippet for embedding."""
    text: str
    section: str          # e.g., 'required', 'preferred', 'responsibilities', 'experience', 'projects', 'skills'
    weight: float = 1.0   # Relative importance in scoring aggregation
    source: str = "jd"    # 'jd' or 'resume'
    metadata: Dict[str, Any] = field(default_factory=dict)


class SemanticMatcher:
    """
    Evaluates contextual and semantic alignment between a Candidate Resume
    and a Job Description using local embeddings (all-MiniLM-L6-v2).

    Principles:
    1. Local & Offline Execution: Operates entirely locally without requiring external APIs
       (Gemini, OpenAI) or active internet connection during scoring.
    2. Section-Aware Decomposition: Avoids crude whole-document cosine similarity. Decomposes
       the JD into requirement/responsibility units and the resume into experience/project/skill
       evidence chunks.
    3. Noise-Floor Calibrated Similarity: Unrelated content (raw cosine <= 0.15) is cleanly
       mapped to 0.0 to prevent false-positive accumulation across disparate fields.
    4. Deterministic & Candidate-Independent: A candidate's score depends solely on their
       alignment with the JD, preserving ranking stability when candidates are added or removed.
    5. Full Explainability: Retains inspectable provenance for strongest semantic matches,
       linking specific JD requirements to explicit resume evidence, preserving original casing.
    """

    DEFAULT_NOISE_THRESHOLD: float = 0.15
    DEFAULT_TOP_MATCHES_COUNT: int = 5

    # Section weights for JD requirements
    JD_SECTION_WEIGHTS = {
        "required": 1.0,
        "preferred": 0.60,
        "responsibilities": 0.30,
        "contextual": 0.10,
        "general": 0.10,
        "other": 0.10
    }

    _model: Any = None
    _embedding_cache: Dict[str, np.ndarray] = {}

    @classmethod
    def get_model(cls, model_name: str = DEFAULT_EMBEDDING_MODEL) -> Any:
        """
        Retrieves or initializes the shared SentenceTransformer embedding model singleton.
        Ensures the model is loaded once in memory and reused across all evaluations.
        """
        if cls._model is None:
            from sentence_transformers import SentenceTransformer
            cls._model = SentenceTransformer(model_name)
        return cls._model

    @classmethod
    def get_embedding_model(cls, model_name: str = DEFAULT_EMBEDDING_MODEL) -> Any:
        """Alias for get_model."""
        return cls.get_model(model_name)

    @classmethod
    def set_model(cls, model: Any) -> None:
        """Allows injecting a custom or mock model for testing purposes."""
        cls._model = model

    @classmethod
    def clear_cache(cls) -> None:
        """Clears the in-memory text embedding cache."""
        cls._embedding_cache.clear()

    # -------------------------------------------------------------------------
    # Chunking & Decomposition
    # -------------------------------------------------------------------------

    @classmethod
    def _clean_snippet(cls, text: str) -> str:
        """
        Cleans typographical symbols, quotes, and whitespace while preserving original casing.
        """
        if not text:
            return ""
        text = text.replace("\u00a0", " ").replace("\u200b", " ").replace("\ufeff", " ")
        text = re.sub(r"[\u2018\u2019]", "'", text)
        text = re.sub(r"[\u201c\u201d]", '"', text)
        text = re.sub(r"[\u2013\u2014]", "-", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @classmethod
    def _clean_and_split_lines(cls, text: str, min_len: int = 3) -> List[str]:
        """Splits text into non-empty, stripped bullet lines or sentences preserving casing."""
        if not text:
            return []
        lines: List[str] = []
        for raw_line in text.split("\n"):
            line = cls._clean_snippet(raw_line)
            # Strip leading bullets, dashes, numbers, etc.
            line = re.sub(r"^[\s\-\*\•\d+\.\)\(\]]+", "", line).strip()
            if len(line) >= min_len:
                lines.append(line)
        return lines

    @classmethod
    def chunk_jd(cls, jd: JobDescription) -> List[TextChunk]:
        """
        Decomposes a Job Description into section-aware semantic requirement chunks:
        - required: Mandatory qualifications and required skills
        - responsibilities: Core role responsibilities and duties
        - preferred: Nice-to-have qualifications
        - general: Title and high-level role summary
        """
        if not jd or (not jd.raw_text and not jd.sections and not jd.required_skills):
            return []

        chunks: List[TextChunk] = []
        seen_texts: Set[str] = set()

        def add_chunk(text: str, section: str, weight: float, meta: Optional[Dict[str, Any]] = None):
            cleaned = cls._clean_snippet(text)
            norm = cleaned.lower()
            if norm and norm not in seen_texts and len(cleaned) >= 3:
                seen_texts.add(norm)
                chunks.append(TextChunk(
                    text=cleaned,
                    section=section,
                    weight=weight,
                    source="jd",
                    metadata=meta or {}
                ))

        # 1. Job Title & General Context
        if jd.title and jd.title != "Unknown Job Title":
            add_chunk(f"Job Role: {jd.title}", "general", cls.JD_SECTION_WEIGHTS["general"])

        # Determine sections dictionary: use parsed sections or segment on the fly
        sections = jd.sections or {}
        if not sections and jd.raw_text:
            sections = JDExtractor.segment_sections(jd.raw_text)

        # 2. Required Section & Skill Evidences
        if jd.skill_evidences:
            for skill, ev in jd.skill_evidences.items():
                if ev.classification == "required" and ev.source_context:
                    add_chunk(ev.source_context, "required", cls.JD_SECTION_WEIGHTS["required"], {"skill": skill})
                elif ev.classification == "preferred" and ev.source_context:
                    add_chunk(ev.source_context, "preferred", cls.JD_SECTION_WEIGHTS["preferred"], {"skill": skill})

        # Process structured 'required' section text
        if "required" in sections:
            for line in cls._clean_and_split_lines(sections["required"]):
                add_chunk(line, "required", cls.JD_SECTION_WEIGHTS["required"])

        # If no required chunks yet but required_skills list is provided
        if not any(c.section == "required" for c in chunks) and jd.required_skills:
            for skill in jd.required_skills:
                add_chunk(f"Proficiency in {skill}", "required", cls.JD_SECTION_WEIGHTS["required"], {"skill": skill})

        # 3. Responsibilities / Contextual Section
        for sec_name in ["contextual", "responsibilities", "about", "overview"]:
            if sec_name in sections:
                for line in cls._clean_and_split_lines(sections[sec_name]):
                    add_chunk(line, "responsibilities", cls.JD_SECTION_WEIGHTS["responsibilities"])

        # 4. Preferred Section
        if "preferred" in sections:
            for line in cls._clean_and_split_lines(sections["preferred"]):
                add_chunk(line, "preferred", cls.JD_SECTION_WEIGHTS["preferred"])

        if not any(c.section == "preferred" for c in chunks) and jd.preferred_skills:
            for skill in jd.preferred_skills:
                add_chunk(f"Experience with {skill}", "preferred", cls.JD_SECTION_WEIGHTS["preferred"], {"skill": skill})

        # 5. General Section
        if "general" in sections:
            for line in cls._clean_and_split_lines(sections["general"]):
                add_chunk(line, "general", cls.JD_SECTION_WEIGHTS["general"])

        # Fallback: If chunks are still empty, parse raw_text directly
        if not chunks and jd.raw_text:
            for line in cls._clean_and_split_lines(jd.raw_text):
                add_chunk(line, "general", cls.JD_SECTION_WEIGHTS["general"])

        return chunks

    @classmethod
    def chunk_resume(cls, resume: Resume) -> List[TextChunk]:
        """
        Decomposes a Resume into semantic evidence chunks:
        - experience: Roles, achievements, and work descriptions
        - projects: Project descriptions, technologies used, and outcomes
        - skills: Technical skills and proficiencies
        - summary: Professional profile and objective
        - education / certifications: Academic background and credentials
        """
        if not resume or (not resume.raw_text and not resume.sections and not resume.skills):
            return []

        chunks: List[TextChunk] = []
        seen_texts: Set[str] = set()

        def add_chunk(text: str, section: str, meta: Optional[Dict[str, Any]] = None):
            cleaned = cls._clean_snippet(text)
            norm = cleaned.lower()
            if norm and norm not in seen_texts and len(cleaned) >= 3:
                seen_texts.add(norm)
                chunks.append(TextChunk(
                    text=cleaned,
                    section=section,
                    weight=1.0,
                    source="resume",
                    metadata=meta or {}
                ))

        # Determine sections dictionary: use parsed sections or segment on the fly
        sections = resume.sections or {}
        if not sections and resume.raw_text:
            sections = ResumeExtractor.extract_sections(resume.raw_text)

        # 1. Summary / Objective / General Opening
        if "summary" in sections:
            for line in cls._clean_and_split_lines(sections["summary"]):
                add_chunk(line, "summary")

        if "general" in sections:
            for line in cls._clean_and_split_lines(sections["general"]):
                add_chunk(line, "summary")

        # 2. Structured Experience Entries (if available)
        if resume.experience_entries:
            for exp in resume.experience_entries:
                header = f"{exp.title} at {exp.company}".strip(" at ")
                if header:
                    add_chunk(header, "experience", {"role": exp.title, "company": exp.company})
                if exp.description:
                    for line in cls._clean_and_split_lines(exp.description):
                        add_chunk(line, "experience", {"role": exp.title})
                if exp.technologies:
                    add_chunk(f"Technologies used: {', '.join(exp.technologies)}", "experience")

        # Raw experience section fallback or complement
        if "experience" in sections:
            for line in cls._clean_and_split_lines(sections["experience"]):
                add_chunk(line, "experience")

        # 3. Structured Project Entries (if available)
        if resume.projects:
            for proj in resume.projects:
                proj_desc = f"Project {proj.name}: {proj.description}".strip(": ")
                add_chunk(proj_desc, "projects", {"name": proj.name})
                if proj.technologies:
                    add_chunk(f"Project technologies: {', '.join(proj.technologies)}", "projects", {"name": proj.name})

        # Raw projects section fallback or complement
        if "projects" in sections:
            for line in cls._clean_and_split_lines(sections["projects"]):
                add_chunk(line, "projects")

        # 4. Skills Section & Explicit Skills
        if "skills" in sections:
            for line in cls._clean_and_split_lines(sections["skills"]):
                add_chunk(line, "skills")

        if resume.skills:
            skills_str = ", ".join(resume.skills)
            add_chunk(f"Technical skills: {skills_str}", "skills")

        # 5. Education & Certifications
        if "education" in sections:
            for line in cls._clean_and_split_lines(sections["education"]):
                add_chunk(line, "education")

        if "certifications" in sections:
            for line in cls._clean_and_split_lines(sections["certifications"]):
                add_chunk(line, "certifications")

        # Fallback: If no chunks were created, parse raw_text
        if not chunks and resume.raw_text:
            for line in cls._clean_and_split_lines(resume.raw_text):
                add_chunk(line, "general")

        return chunks

    # -------------------------------------------------------------------------
    # Embedding & Similarity Computation
    # -------------------------------------------------------------------------

    @classmethod
    def _encode_texts(cls, texts: List[str], batch_size: int = 64) -> np.ndarray:
        """
        Encodes a list of text strings into normalized L2 embeddings.
        Utilizes the class-level embedding cache to avoid redundant encoding.
        """
        if not texts:
            return np.empty((0, 384), dtype=np.float32)

        # Identify texts requiring encoding
        uncached: List[str] = []
        for t in texts:
            if t not in cls._embedding_cache:
                uncached.append(t)

        # Batch encode uncached texts
        if uncached:
            # Deduplicate uncached strings before inference
            unique_uncached = list(dict.fromkeys(uncached))
            model = cls.get_model()
            new_embeddings = model.encode(
                unique_uncached,
                batch_size=batch_size,
                show_progress_bar=False,
                normalize_embeddings=True,
                convert_to_numpy=True
            )
            for text, emb in zip(unique_uncached, new_embeddings):
                cls._embedding_cache[text] = emb.astype(np.float32)

        # Assemble full matrix
        embeddings = np.array([cls._embedding_cache[t] for t in texts], dtype=np.float32)
        return embeddings

    @classmethod
    def _calibrate_similarity(cls, raw_sim: float, noise_threshold: float) -> float:
        """
        Maps raw cosine similarity to calibrated similarity in [0.0, 1.0].
        Scores at or below noise_threshold are zeroed out to prevent noise accumulation.
        Scores above noise_threshold are scaled linearly to [0.0, 1.0].
        """
        if np.isnan(raw_sim) or np.isinf(raw_sim):
            return 0.0
        if raw_sim <= noise_threshold:
            return 0.0
        calibrated = (raw_sim - noise_threshold) / (1.0 - noise_threshold)
        return max(0.0, min(1.0, float(calibrated)))

    # -------------------------------------------------------------------------
    # Core Matching Logic
    # -------------------------------------------------------------------------

    @classmethod
    def match(
        cls,
        jd: JobDescription,
        candidate: Union[Resume, CandidateResult],
        config: Optional[RankingConfig] = None,
        top_k_matches: int = DEFAULT_TOP_MATCHES_COUNT,
        noise_threshold: float = DEFAULT_NOISE_THRESHOLD
    ) -> CandidateResult:
        """
        Evaluates semantic similarity between a Job Description and a Candidate Resume.
        Populates CandidateResult.semantic_breakdown with bounded score [0.0, 1.0]
        and inspectable evidence.
        """
        cfg = config or DEFAULT_RANKING_CONFIG

        if isinstance(candidate, CandidateResult):
            resume = candidate.resume
            result_obj = candidate
        else:
            resume = candidate
            result_obj = CandidateResult(
                resume=resume,
                keyword_breakdown=KeywordScoreBreakdown(),
                semantic_breakdown=SemanticScoreBreakdown(),
                penalties=PenaltyBreakdown(),
                final_score=0.0,
                ranking_reason=""
            )

        # 1. Chunk both documents
        jd_chunks = cls.chunk_jd(jd)
        resume_chunks = cls.chunk_resume(resume)

        if not jd_chunks or not resume_chunks:
            error_reason = "Empty or unparseable JD" if not jd_chunks else "Empty or unparseable resume"
            result_obj.semantic_breakdown = SemanticScoreBreakdown(
                score=0.0,
                strongest_matches=[],
                similarity_evidence={
                    "error": error_reason,
                    "jd_chunks_evaluated": len(jd_chunks),
                    "resume_chunks_evaluated": len(resume_chunks)
                }
            )
            return result_obj

        # 2. Encode all chunks
        jd_texts = [c.text for c in jd_chunks]
        resume_texts = [c.text for c in resume_chunks]

        jd_embs = cls._encode_texts(jd_texts)
        resume_embs = cls._encode_texts(resume_texts)

        # 3. Compute cosine similarity matrix: shape (M_jd, N_resume)
        sim_matrix = np.dot(jd_embs, resume_embs.T)

        # 4. Evaluate each JD requirement against candidate evidence
        all_matches: List[Dict[str, Any]] = []
        section_scores_accum: Dict[str, List[float]] = {}
        weighted_score_sum = 0.0
        total_weight = 0.0

        for i, q in enumerate(jd_chunks):
            row_sims = sim_matrix[i]
            best_idx = int(np.argmax(row_sims))
            raw_sim = float(row_sims[best_idx])
            calibrated_sim = cls._calibrate_similarity(raw_sim, noise_threshold)

            best_resume_chunk = resume_chunks[best_idx]
            match_record = {
                "jd_chunk": q.text,
                "jd_section": q.section,
                "resume_chunk": best_resume_chunk.text,
                "resume_section": best_resume_chunk.section,
                "similarity": round(calibrated_sim, 4),
                "raw_similarity": round(raw_sim, 4),
                "weight": q.weight
            }
            all_matches.append(match_record)

            if q.section not in section_scores_accum:
                section_scores_accum[q.section] = []
            section_scores_accum[q.section].append(calibrated_sim)

            weighted_score_sum += calibrated_sim * q.weight
            total_weight += q.weight

        # 5. Aggregate overall semantic score
        if total_weight > 0.0:
            semantic_score = round(max(0.0, min(1.0, weighted_score_sum / total_weight)), 4)
        else:
            semantic_score = 0.0

        # 6. Extract Top-K Strongest Matches for evidence
        sorted_matches = sorted(
            all_matches,
            key=lambda m: (-m["raw_similarity"], m["jd_chunk"], m["resume_chunk"])
        )
        strongest_matches = [
            {
                "jd_chunk": m["jd_chunk"],
                "jd_section": m["jd_section"],
                "resume_chunk": m["resume_chunk"],
                "resume_section": m["resume_section"],
                "similarity": m["similarity"],
                "raw_similarity": m["raw_similarity"]
            }
            for m in sorted_matches[:top_k_matches]
        ]

        # 7. Section-level breakdown
        section_averages = {
            sec: round(float(np.mean(scores)), 4)
            for sec, scores in section_scores_accum.items()
        }

        similarity_evidence = {
            "section_scores": section_averages,
            "jd_chunks_evaluated": len(jd_chunks),
            "resume_chunks_evaluated": len(resume_chunks),
            "noise_threshold": noise_threshold,
            "all_matches_count": len(all_matches)
        }

        # 8. Populate result
        result_obj.semantic_breakdown = SemanticScoreBreakdown(
            score=semantic_score,
            strongest_matches=strongest_matches,
            similarity_evidence=similarity_evidence
        )

        return result_obj

    # -------------------------------------------------------------------------
    # Batch Processing API
    # -------------------------------------------------------------------------

    @classmethod
    def match_batch(
        cls,
        jd: JobDescription,
        candidates: List[Union[Resume, CandidateResult]],
        config: Optional[RankingConfig] = None,
        top_k_matches: int = DEFAULT_TOP_MATCHES_COUNT,
        noise_threshold: float = DEFAULT_NOISE_THRESHOLD
    ) -> List[CandidateResult]:
        """
        Batch-evaluates candidate resumes against a Job Description.
        Encodes all JD chunks and all unique candidate chunks in batched model calls.
        Returns CandidateResult objects sorted descending by semantic_score.
        """
        if not candidates:
            return []

        # 1. Chunk JD once
        jd_chunks = cls.chunk_jd(jd)

        # 2. Chunk all candidate resumes
        parsed_candidates: List[Tuple[CandidateResult, Resume, List[TextChunk]]] = []
        all_candidate_texts: List[str] = []

        for item in candidates:
            if isinstance(item, CandidateResult):
                cand_res = item
                resume = item.resume
            else:
                resume = item
                cand_res = CandidateResult(
                    resume=resume,
                    keyword_breakdown=KeywordScoreBreakdown(),
                    semantic_breakdown=SemanticScoreBreakdown(),
                    penalties=PenaltyBreakdown(),
                    final_score=0.0,
                    ranking_reason=""
                )

            r_chunks = cls.chunk_resume(resume)
            parsed_candidates.append((cand_res, resume, r_chunks))
            all_candidate_texts.extend([c.text for c in r_chunks])

        # 3. Batch encode JD chunks and all candidate texts together
        if jd_chunks:
            jd_texts = [c.text for c in jd_chunks]
            cls._encode_texts(jd_texts)

        if all_candidate_texts:
            cls._encode_texts(all_candidate_texts)

        # 4. Evaluate each candidate using pre-computed embeddings
        results: List[CandidateResult] = []
        for cand_res, resume, r_chunks in parsed_candidates:
            if not jd_chunks or not r_chunks:
                error_reason = "Empty or unparseable JD" if not jd_chunks else "Empty or unparseable resume"
                cand_res.semantic_breakdown = SemanticScoreBreakdown(
                    score=0.0,
                    strongest_matches=[],
                    similarity_evidence={
                        "error": error_reason,
                        "jd_chunks_evaluated": len(jd_chunks),
                        "resume_chunks_evaluated": len(r_chunks)
                    }
                )
                results.append(cand_res)
                continue

            jd_embs = np.array([cls._embedding_cache[c.text] for c in jd_chunks], dtype=np.float32)
            r_embs = np.array([cls._embedding_cache[c.text] for c in r_chunks], dtype=np.float32)

            sim_matrix = np.dot(jd_embs, r_embs.T)

            all_matches: List[Dict[str, Any]] = []
            section_scores_accum: Dict[str, List[float]] = {}
            weighted_score_sum = 0.0
            total_weight = 0.0

            for i, q in enumerate(jd_chunks):
                row_sims = sim_matrix[i]
                best_idx = int(np.argmax(row_sims))
                raw_sim = float(row_sims[best_idx])
                calibrated_sim = cls._calibrate_similarity(raw_sim, noise_threshold)

                best_r_chunk = r_chunks[best_idx]
                match_record = {
                    "jd_chunk": q.text,
                    "jd_section": q.section,
                    "resume_chunk": best_r_chunk.text,
                    "resume_section": best_r_chunk.section,
                    "similarity": round(calibrated_sim, 4),
                    "raw_similarity": round(raw_sim, 4),
                    "weight": q.weight
                }
                all_matches.append(match_record)

                if q.section not in section_scores_accum:
                    section_scores_accum[q.section] = []
                section_scores_accum[q.section].append(calibrated_sim)

                weighted_score_sum += calibrated_sim * q.weight
                total_weight += q.weight

            semantic_score = round(max(0.0, min(1.0, weighted_score_sum / total_weight)), 4) if total_weight > 0 else 0.0

            sorted_matches = sorted(
                all_matches,
                key=lambda m: (-m["raw_similarity"], m["jd_chunk"], m["resume_chunk"])
            )
            strongest_matches = [
                {
                    "jd_chunk": m["jd_chunk"],
                    "jd_section": m["jd_section"],
                    "resume_chunk": m["resume_chunk"],
                    "resume_section": m["resume_section"],
                    "similarity": m["similarity"],
                    "raw_similarity": m["raw_similarity"]
                }
                for m in sorted_matches[:top_k_matches]
            ]

            section_averages = {
                sec: round(float(np.mean(scores)), 4)
                for sec, scores in section_scores_accum.items()
            }

            cand_res.semantic_breakdown = SemanticScoreBreakdown(
                score=semantic_score,
                strongest_matches=strongest_matches,
                similarity_evidence={
                    "section_scores": section_averages,
                    "jd_chunks_evaluated": len(jd_chunks),
                    "resume_chunks_evaluated": len(r_chunks),
                    "noise_threshold": noise_threshold,
                    "all_matches_count": len(all_matches)
                }
            )
            results.append(cand_res)

        # Sort descending by semantic score; tie-break deterministically by candidate name
        results.sort(key=lambda r: (-r.semantic_score, r.resume.candidate_name))
        return results
