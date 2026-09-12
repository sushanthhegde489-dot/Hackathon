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

    # Comprehensive vocabulary of tech skills to search for
    TECH_SKILLS_VOCAB = [
        # Languages
        "python", "javascript", "typescript", "java", "c++", "c#", ".net", "go", "ruby", "php", "swift", "kotlin", "rust",
        # Frontend
        "react", "react native", "angular", "vue", "next.js", "svelte", "jquery", "bootstrap", "tailwind", "html", "css",
        # Backend & Frameworks
        "node.js", "express", "django", "flask", "fastapi", "spring boot", "laravel", "rails",
        # Databases & Caching
        "mongodb", "postgresql", "mysql", "redis", "sqlite", "sql server", "dynamodb", "nosql",
        # Cloud & DevOps
        "aws", "azure", "gcp", "docker", "kubernetes", "git", "ci/cd", "jenkins", "terraform",
        # APIs & Architecture
        "rest api", "rest", "graphql", "grpc", "microservices", "json",
        # Testing
        "jest", "mocha", "chai", "cypress", "selenium", "junit", "pytest",
        # Methodologies & Tools
        "agile", "scrum", "jira"
    ]

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

    # The Hackathon specifically requires recognizing that a candidate with "Express"
    # is relevant for a "Node.js" role, even if "Node.js" is not literally in the resume.
    # This graph maps a canonical skill to a set of skills that semantically satisfy it.
    RELATED_SKILLS_GRAPH: Dict[str, Set[str]] = {
        "nodejs": {"express", "nestjs", "javascript", "typescript", "rest api"},
        "express": {"nodejs", "javascript", "typescript", "rest api"},
        "javascript": {"typescript", "react", "nodejs", "express", "angular", "vue"},
        "typescript": {"javascript", "react", "nodejs", "express", "angular", "vue"},
        "react": {"nextjs", "javascript", "typescript", "redux"},
        "mongodb": {"nosql", "dynamodb", "documentdb"},
        "postgresql": {"sql", "mysql", "mssql", "sqlite"},
        "mysql": {"sql", "postgresql", "mssql", "sqlite"},
        "sql": {"postgresql", "mysql", "mssql", "sqlite"},
        "nosql": {"mongodb", "dynamodb", "redis", "cassandra"},
        "aws": {"cloud", "azure", "gcp"},
        "azure": {"cloud", "aws", "gcp"},
        "gcp": {"cloud", "aws", "azure"},
        "rest api": {"json", "express", "fastapi", "flask", "django", "spring boot"},
        "json": {"rest api", "api", "javascript"},
        "docker": {"kubernetes", "containerization", "ci/cd"},
        "kubernetes": {"docker", "containerization", "ci/cd"},
        "ci/cd": {"jenkins", "github actions", "gitlab ci", "docker", "kubernetes"}
    }

    @classmethod
    def get_equivalent_skills(cls, canonical_skill: str) -> Set[str]:
        """Returns a set of skills that are semantically equivalent or strongly imply the canonical skill."""
        equiv = {canonical_skill}
        if canonical_skill in cls.RELATED_SKILLS_GRAPH:
            equiv.update(cls.RELATED_SKILLS_GRAPH[canonical_skill])
        return equiv

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
