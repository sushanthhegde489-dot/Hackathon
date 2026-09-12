import re

with open("tests/test_keyword_matcher.py", "r", encoding="utf-8") as f:
    content = f.read()
content = re.sub(
    r"def test_node_vs_django\(self, config\):",
    "def test_node_vs_django(self):",
    content
)
content = re.sub(
    r"result = KeywordMatcher\.match\(jd, resume, config\)",
    "result = KeywordMatcher.match(jd, resume)",
    content
)
with open("tests/test_keyword_matcher.py", "w", encoding="utf-8") as f:
    f.write(content)

with open("tests/test_hybrid_ranker.py", "r", encoding="utf-8") as f:
    content2 = f.read()

content2 = re.sub(
    r"assert res.final_score == res.semantic_score",
    "assert res.final_score == round(max(0.0, res.semantic_score - res.penalties.total_penalty), 4)",
    content2
)

with open("tests/test_hybrid_ranker.py", "w", encoding="utf-8") as f:
    f.write(content2)
