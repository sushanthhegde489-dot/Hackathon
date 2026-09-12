import pytest
from extraction.skill_normalizer import SkillNormalizer

class TestSkillNormalizer:
    def test_canonical_equivalences(self):
        # Specific examples required by specifications
        assert SkillNormalizer.normalize("js") == "javascript"
        assert SkillNormalizer.normalize("ts") == "typescript"
        assert SkillNormalizer.normalize("node.js") == "nodejs"
        assert SkillNormalizer.normalize("react.js") == "react"
        assert SkillNormalizer.normalize("express.js") == "express"
        assert SkillNormalizer.normalize("mongo") == "mongodb"
        assert SkillNormalizer.normalize("restful API") == "rest api"
        assert SkillNormalizer.normalize("rest apis") == "rest api"

    def test_framework_and_library_synonyms(self):
        assert SkillNormalizer.normalize("reactjs") == "react"
        assert SkillNormalizer.normalize("vue.js") == "vue"
        assert SkillNormalizer.normalize("angular.js") == "angular"
        assert SkillNormalizer.normalize("next.js") == "nextjs"
        assert SkillNormalizer.normalize("golang") == "go"
        assert SkillNormalizer.normalize("cpp") == "c++"
        assert SkillNormalizer.normalize("csharp") == "c#"
        assert SkillNormalizer.normalize("dotnet") == ".net"
        assert SkillNormalizer.normalize("k8s") == "kubernetes"
        assert SkillNormalizer.normalize("cicd") == "ci/cd"
        assert SkillNormalizer.normalize("amazon web services") == "aws"

    def test_strictly_no_false_equivalence_between_distinct_technologies(self):
        # React != JavaScript
        assert SkillNormalizer.normalize("react") != SkillNormalizer.normalize("javascript")

        # Node.js != Express
        assert SkillNormalizer.normalize("node.js") != SkillNormalizer.normalize("express")

        # MongoDB != SQL
        assert SkillNormalizer.normalize("mongodb") != SkillNormalizer.normalize("sql")
        assert SkillNormalizer.normalize("mongodb") != SkillNormalizer.normalize("mysql")
        assert SkillNormalizer.normalize("mongodb") != SkillNormalizer.normalize("postgresql")

        # AWS != Docker
        assert SkillNormalizer.normalize("aws") != SkillNormalizer.normalize("docker")

        # Java != JavaScript
        assert SkillNormalizer.normalize("java") != SkillNormalizer.normalize("javascript")

        # C != C++ != C#
        assert SkillNormalizer.normalize("c") != SkillNormalizer.normalize("c++")
        assert SkillNormalizer.normalize("c++") != SkillNormalizer.normalize("c#")

    def test_normalize_list_deduplicates_and_sorts(self):
        skills = ["React.js", "react", "JavaScript", "js", "Docker", "k8s", "kubernetes"]
        normalized = SkillNormalizer.normalize_list(skills)
        assert normalized == ["docker", "javascript", "kubernetes", "react"]

    def test_empty_and_invalid_inputs(self):
        assert SkillNormalizer.normalize("") == ""
        assert SkillNormalizer.normalize(None) == ""
        assert SkillNormalizer.normalize_list([]) == []
        assert SkillNormalizer.normalize_list(None) == []
