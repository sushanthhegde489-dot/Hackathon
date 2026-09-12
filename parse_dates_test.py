import re

def extract_experience_years_from_text(raw_text):
    if not raw_text:
        return 0.0

    text = raw_text.lower()
    
    # 1. Look for explicit stated years
    explicit_years = 0.0
    patterns = [
        r"experience\s*(?:required)?\s*:\s*(\d+(?:\.\d+)?)\s*(?:\+|-)?\s*year[s]?",
        r"(\d+(?:\.\d+)?)\s*(?:to|-)\s*\d+(?:\.\d+)?\s*year[s]?",
        r"(\d+(?:\.\d+)?)\s*(?:\+|-)?\s*year[s]?(?:\s+of)?\s+(?:[a-z\s]{0,35})?\s*experience",
        r"experience\s*(?:of\s*)?(?:at\s*least\s*)?(\d+(?:\.\d+)?)\s*year[s]?",
        r"minimum\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:\+)?\s*year[s]?",
        r"(\d+(?:\.\d+)?)\s*\+\s*years\b"
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            try:
                explicit_years = float(matches[0])
                break
            except:
                pass

    # 2. Look for date ranges like "Jan 2020 - Mar 2023" or "2019 to Present"
    date_pattern = re.compile(
        r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december)?\s*"
        r"(20\d{2})\s*(?:-|to|–)\s*"
        r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december|present|current|now)?\s*"
        r"(20\d{2})?",
        re.IGNORECASE
    )
    
    parsed_years = 0.0
    # To prevent overlapping counting, keep track of found years
    for match in date_pattern.findall(text):
        start_year_str, end_year_str = match
        try:
            start_year = int(start_year_str)
            end_year = int(end_year_str) if end_year_str else 2024
            
            diff = end_year - start_year
            if 0 < diff < 15:
                parsed_years += diff
        except:
            continue

    return max(explicit_years, parsed_years)

print(extract_experience_years_from_text("Software Engineer\nTechNova\nJan 2020 - Mar 2023\nDid stuff.\nIntern\nXYZ Corp\n2019 to 2020"))
print(extract_experience_years_from_text("5 years of experience in backend"))
print(extract_experience_years_from_text("Mar 2021 – Present"))
