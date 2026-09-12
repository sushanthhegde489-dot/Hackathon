from typing import Dict, List, Set

class SkillNormalizer:
    """Normalizes tech skill names to handle common variations and synonyms."""
    
    # Common synonyms mapping to a standardized form
    SYNONYMS_MAP: Dict[str, str] = {
        # Languages & Runtimes
        "javascript": "javascript",
        "js": "javascript",
        "typescript": "typescript",
        "ts": "typescript",
        "golang": "go",
        "python3": "python",
        "py": "python",
        "node": "nodejs",
        "node.js": "nodejs",
        "nodejs": "nodejs",
        
        # Frontend Frameworks
        "react": "react",
        "reactjs": "react",
        "react.js": "react",
        "vue": "vue",
        "vuejs": "vue",
        "vue.js": "vue",
        "angularjs": "angular",
        "angular.js": "angular",
        "angular": "angular",
        
        # Backend Frameworks & DBs
        "express": "express",
        "expressjs": "express",
        "express.js": "express",
        "mongodb": "mongodb",
        "mongo": "mongodb",
        "postgresql": "postgres",
        "postgres": "postgres",
        "sqlserver": "mssql",
        "ms sql": "mssql",
        
        # Cloud & DevOps
        "aws": "amazon web services",
        "amazon web services": "amazon web services",
        "gcp": "google cloud platform",
        "google cloud": "google cloud platform",
        "k8s": "kubernetes",
        "docker": "docker",
        
        # Core Tech Concepts
        "rest": "rest api",
        "restful": "rest api",
        "rest api": "rest api",
        "rest apis": "rest api",
    }

    @classmethod
    def normalize(cls, skill: str) -> str:
        """Normalizes a single skill string."""
        s = skill.strip().lower()
        return cls.SYNONYMS_MAP.get(s, s)

    @classmethod
    def normalize_list(cls, skills: List[str]) -> List[str]:
        """Normalizes a list of skills and removes duplicates."""
        normalized_set: Set[str] = set()
        for s in skills:
            normalized_set.add(cls.normalize(s))
        return sorted(list(normalized_set))
