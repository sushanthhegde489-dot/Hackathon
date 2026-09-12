import re
from typing import List, Optional

class TextCleaner:
    """
    Robust text cleaner and tokenizer designed for technical resumes and job descriptions.
    Preserves critical technical tokens including:
    - C++, G++
    - C#, F#
    - .NET, .NET Core, ASP.NET
    - Node.js, Next.js, React.js, Vue.js
    - CI/CD
    - REST API / RESTful APIs
    """

    # Regex pattern to accurately capture words while preserving technical entities:
    # 1. Specific compound technical acronyms like ci/cd
    # 2. Trailing ++ tokens (e.g. c++, g++)
    # 3. Trailing # tokens (e.g. c#, f#)
    # 4. Leading dot tokens (e.g. .net)
    # 5. General tokens with internal dots/hyphens (e.g. node.js, next.js, react.js, asp.net, full-stack)
    TOKEN_PATTERN = re.compile(
        r"\bci/cd\b|"
        r"\b[a-z0-9]+(?:\.[a-z0-9]+)*\+\+|"
        r"\b[a-z0-9]+\#|"
        r"(?:\.[a-z0-9]+)+\b|"
        r"\b[a-z0-9]+(?:[-.][a-z0-9]+)*\b",
        re.IGNORECASE
    )

    @staticmethod
    def clean_text(text: Optional[str]) -> str:
        """
        Performs text normalization:
        1. Handles None and non-string inputs gracefully.
        2. Normalizes whitespace, tabs, and newlines into single spaces.
        3. Normalizes non-standard unicode quotation marks, dashes, and bullet points.
        4. Lowercases the entire text.
        5. Preserves technical symbols (+, #, ., /, -).
        """
        if text is None:
            return ""
        if not isinstance(text, str):
            text = str(text)

        # Replace non-breaking and unusual whitespace characters
        text = text.replace("\u00a0", " ").replace("\u200b", " ").replace("\ufeff", " ")
        
        # Normalize typographic quotes and dashes
        text = re.sub(r"[\u2018\u2019]", "'", text)
        text = re.sub(r"[\u201c\u201d]", '"', text)
        text = re.sub(r"[\u2013\u2014]", "-", text)

        # Collapse multiple whitespace characters into a single space
        text = re.sub(r"\s+", " ", text)

        return text.strip().lower()

    @staticmethod
    def extract_words(text: Optional[str]) -> List[str]:
        """
        Tokenizes text into lowercase tokens, keeping technical symbols (+, #, ., /) intact.
        Guarantees that:
        - 'C++' -> 'c++'
        - 'C#' -> 'c#'
        - '.NET' -> '.net'
        - 'Node.js' -> 'node.js'
        - 'CI/CD' -> 'ci/cd'
        - 'React.js' -> 'react.js'
        """
        if not text:
            return []

        cleaned = TextCleaner.clean_text(text)
        if not cleaned:
            return []

        matches = TextCleaner.TOKEN_PATTERN.findall(cleaned)
        return [m.lower() for m in matches if m]
