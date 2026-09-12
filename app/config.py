from pathlib import Path
from dataclasses import dataclass

# Repository-relative paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
JD_DIR = DATA_DIR / "jd"
RESUMES_DIR = DATA_DIR / "resumes"

TEST_DIR = BASE_DIR / "tests"
TEST_DATA_DIR = TEST_DIR / "data"
TEST_JD_DIR = TEST_DATA_DIR / "jd"
TEST_RESUMES_DIR = TEST_DATA_DIR / "resumes"
TEST_FIXTURE_DIR = TEST_DIR / "test_fixtures"

# Local embedding model: use bundled copy if present, otherwise let sentence-transformers fetch it
_LOCAL_MODEL_DIR = BASE_DIR / "models" / "all-MiniLM-L6-v2"
DEFAULT_EMBEDDING_MODEL = str(_LOCAL_MODEL_DIR) if _LOCAL_MODEL_DIR.exists() else "all-MiniLM-L6-v2"


@dataclass
class RankingConfig:
    """
    Scoring weights and penalty parameters for the hybrid ranker.

    Defaults are calibrated against the project's adversarial benchmark corpus
    (see RANKING_CALIBRATION.md). Adjust via the Streamlit sidebar to experiment
    with alternative operating points.

    keyword_weight + semantic_weight must sum to 1.0.
    """
    keyword_weight: float = 0.40
    semantic_weight: float = 0.60
    required_skill_weight: float = 0.70     # Weight within keyword score
    preferred_skill_weight: float = 0.30    # Weight within keyword score
    contextual_skill_weight: float = 0.00   # Contextual mentions carry no direct score
    experience_penalty_per_year: float = 0.05   # Score deducted per year of experience gap
    maximum_experience_penalty: float = 0.20    # Hard cap on experience penalty
    semantic_noise_threshold: float = 0.18      # Empirically calibrated noise floor

    def validate(self) -> None:
        """Raises ValueError if configuration invariants are violated."""
        if self.keyword_weight < 0.0:
            raise ValueError(f"keyword_weight must be non-negative, got {self.keyword_weight}")
        if self.semantic_weight < 0.0:
            raise ValueError(f"semantic_weight must be non-negative, got {self.semantic_weight}")
        if abs((self.keyword_weight + self.semantic_weight) - 1.0) > 1e-6:
            raise ValueError(
                f"keyword_weight ({self.keyword_weight}) + semantic_weight ({self.semantic_weight}) "
                f"must sum to 1.0, got {self.keyword_weight + self.semantic_weight:.6f}"
            )
        if self.required_skill_weight < 0.0 or self.preferred_skill_weight < 0.0:
            raise ValueError("Skill weights must be non-negative")
        if self.experience_penalty_per_year < 0.0:
            raise ValueError(f"experience_penalty_per_year must be non-negative, got {self.experience_penalty_per_year}")
        if self.maximum_experience_penalty < 0.0:
            raise ValueError(f"maximum_experience_penalty must be non-negative, got {self.maximum_experience_penalty}")


DEFAULT_RANKING_CONFIG = RankingConfig()

# Convenience aliases consumed by legacy test fixtures
DEFAULT_KEYWORD_WEIGHT = DEFAULT_RANKING_CONFIG.keyword_weight
DEFAULT_SEMANTIC_WEIGHT = DEFAULT_RANKING_CONFIG.semantic_weight


def ensure_directories() -> None:
    """Create data directories required for demo and test operation."""
    for directory in [JD_DIR, RESUMES_DIR, TEST_JD_DIR, TEST_RESUMES_DIR, TEST_FIXTURE_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
