from typing import Dict, List, Set, Optional

class SkillNormalizer:
    """
    Normalizes tech skill names to canonical forms ONLY when there is strict equivalence.
    
    IMPORTANT: Merely related technologies are strictly NOT treated as identical.
    - React != JavaScript
    - Node.js != Express
    - MongoDB != SQL
    - AWS != Docker
    - Java != JavaScript
    - C != C++ != C#
    """

    # Equivalence mappings to canonical skill identifiers
    SYNONYMS_MAP: Dict[str, str] = {
        # JavaScript / TypeScript
        "javascript": "javascript",
        "js": "javascript",
        "typescript": "typescript",
        "ts": "typescript",

        # Python
        "python": "python",
        "python3": "python",
        "py": "python",

        # Node / Backend
        "node": "nodejs",
        "node.js": "nodejs",
        "nodejs": "nodejs",
        "express": "express",
        "expressjs": "express",
        "express.js": "express",

        # Frontend Frameworks
        "react": "react",
        "reactjs": "react",
        "react.js": "react",
        "vue": "vue",
        "vuejs": "vue",
        "vue.js": "vue",
        "angular": "angular",
        "angularjs": "angular",
        "angular.js": "angular",
        "next": "nextjs",
        "next.js": "nextjs",
        "nextjs": "nextjs",

        # Databases
        "mongo": "mongodb",
        "mongodb": "mongodb",
        "postgres": "postgresql",
        "postgresql": "postgresql",
        "sql server": "mssql",
        "sqlserver": "mssql",
        "ms sql": "mssql",
        "mssql": "mssql",
        "mysql": "mysql",
        "redis": "redis",
        "sqlite": "sqlite",

        # Cloud & Containerization (Strictly distinct)
        "aws": "aws",
        "amazon web services": "aws",
        "gcp": "gcp",
        "google cloud": "gcp",
        "google cloud platform": "gcp",
        "azure": "azure",
        "microsoft azure": "azure",
        "docker": "docker",
        "k8s": "kubernetes",
        "kubernetes": "kubernetes",

        # CI/CD & DevOps
        "ci/cd": "ci/cd",
        "cicd": "ci/cd",
        "continuous integration": "ci/cd",
        "jenkins": "jenkins",
        "terraform": "terraform",

        # APIs & Architecture
        "rest": "rest api",
        "restful": "rest api",
        "rest api": "rest api",
        "rest apis": "rest api",
        "restful api": "rest api",
        "restful apis": "rest api",
        "graphql": "graphql",
        "grpc": "grpc",
        "microservices": "microservices",

        # Systems & Compiled Languages
        "golang": "go",
        "go": "go",
        "c++": "c++",
        "cpp": "c++",
        "c#": "c#",
        "csharp": "c#",
        ".net": ".net",
        "dotnet": ".net",
        ".net core": ".net",
        "asp.net": ".net",
        "rust": "rust",
        "java": "java",
        "kotlin": "kotlin",
        "swift": "swift",
        "ruby": "ruby",
        "rails": "rails",
        "ruby on rails": "rails",
        "django": "django",
        "flask": "flask",
        "fastapi": "fastapi",
        "spring boot": "spring boot",
        "spring": "spring boot",
        "tailwind": "tailwind",
        "tailwindcss": "tailwind",
        "bootstrap": "bootstrap",
        "git": "git",
    }

    @classmethod
    def normalize(cls, skill: Optional[str]) -> str:
        """Normalizes a single skill string to its canonical representation."""
        if not skill or not isinstance(skill, str):
            return ""
        cleaned = skill.strip().lower()
        return cls.SYNONYMS_MAP.get(cleaned, cleaned)

    @classmethod
    def normalize_list(cls, skills: Optional[List[str]]) -> List[str]:
        """Normalizes a list of skills and removes duplicates while preserving sorted order."""
        if not skills:
            return []
        normalized_set: Set[str] = set()
        for s in skills:
            norm = cls.normalize(s)
            if norm:
                normalized_set.add(norm)
        return sorted(list(normalized_set))
