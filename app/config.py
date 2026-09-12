import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
JD_DIR = DATA_DIR / "jd"
RESUMES_DIR = DATA_DIR / "resumes"

# Test Paths
TEST_DIR = BASE_DIR / "tests"
TEST_DATA_DIR = TEST_DIR / "data"
TEST_JD_DIR = TEST_DATA_DIR / "jd"
TEST_RESUMES_DIR = TEST_DATA_DIR / "resumes"
TEST_FIXTURE_DIR = TEST_DIR / "test_fixtures"

# Models
# Default lightweight CPU embedding model
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

from dataclasses import dataclass

# Ranking Configuration
@dataclass
class RankingConfig:
    """
    Provisional ranking configuration.
    
    IMPORTANT: These weights and parameters are temporary configuration defaults.
    They are PROVISIONAL and must NOT be locked prematurely. Eventual weights
    must be empirically calibrated and justified using real candidate matching behavior
    and test benchmark data.
    """
    keyword_weight: float = 0.40
    semantic_weight: float = 0.60
    required_skill_weight: float = 0.70    # Priority within keyword score
    preferred_skill_weight: float = 0.30   # Priority within keyword score
    contextual_skill_weight: float = 0.00  # Contextual mentions carry zero or minimal direct score
    min_experience_penalty_factor: float = 0.05
    experience_penalty_per_year: float = 0.05   # Penalty deducted per year of experience gap
    maximum_experience_penalty: float = 0.20    # Maximum cap on experience penalty
    semantic_noise_threshold: float = 0.18      # Calibrated noise threshold for semantic matching

    def validate(self) -> None:
        """Validates configuration bounds and invariants."""
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

# Provisional default instance
DEFAULT_RANKING_CONFIG = RankingConfig()

# Temporary backwards-compatible aliases (PROVISIONAL)
DEFAULT_KEYWORD_WEIGHT = DEFAULT_RANKING_CONFIG.keyword_weight
DEFAULT_SEMANTIC_WEIGHT = DEFAULT_RANKING_CONFIG.semantic_weight

def ensure_directories():
    """Ensure that the necessary data and testing directories exist."""
    directories = [
        JD_DIR,
        RESUMES_DIR,
        TEST_JD_DIR,
        TEST_RESUMES_DIR,
        TEST_FIXTURE_DIR,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

ensure_directories()
