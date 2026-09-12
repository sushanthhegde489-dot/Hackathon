import re

class TextCleaner:
    """Helper class for text cleaning and normalization."""

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Performs basic text cleaning:
        1. Decodes bytes if necessary (not needed if already str).
        2. Normalizes multiple newlines and spaces.
        3. Keeps punctuation like ++, #, . (e.g. C++, C#, .NET) but strips others.
        4. Lowercases.
        """
        if not text:
            return ""

        # Normalize unicode spaces
        text = re.sub(r"\s+", " ", text)
        
        # Lowercase
        text = text.lower().strip()
        
        return text

    @staticmethod
    def extract_words(text: str) -> list[str]:
        """
        Tokenizes the text into lowercase words/tokens, keeping special symbols like ++, #, .net.
        This is critical for accurate keyword/skill extraction.
        """
        cleaned = TextCleaner.clean_text(text)
        if not cleaned:
            return []

        # Find word tokens including technical specials like: c++, c#, .net, node.js
        # Pattern matches:
        # 1. Words with trailing ++ (like c++)
        # 2. Words with trailing # (like c#)
        # 3. Leading dot followed by letters (like .net)
        # 4. Standard words with optional dots or hyphens inside (like node.js, full-stack)
        pattern = r"\b[a-z0-9]+(?:\.[a-z0-9]+)*\+\+|[a-z0-9]+\#|(?:\.[a-z0-9]+)+\b|\b[a-z0-9]+(?:[-.][a-z0-9]+)*\b"
        
        tokens = re.findall(pattern, cleaned)
        return tokens
