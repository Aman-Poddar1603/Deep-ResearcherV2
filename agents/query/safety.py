import re

INJECTION_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"reveal\s+system\s+prompt",
    r"bypass\s+safety",
    r"do\s+exactly\s+what\s+i\s+say",
]

UNSAFE_CATEGORIES = {
    "hate": ["hate", "racist", "kill all"],
    "violence": ["kill", "murder", "attack"],
    "sexual": ["porn", "sex", "nude"],
    "self_harm": ["suicide", "kill myself"],
    "illegal": ["hack", "steal", "exploit"],
    "political": ["propaganda", "influence voters"],
}


def detect_prompt_injection(query: str) -> bool:
    query = query.lower()
    return any(re.search(pattern, query) for pattern in INJECTION_PATTERNS)


def detect_safety_issues(query: str) -> list:
    query = query.lower()
    issues = []

    for category, keywords in UNSAFE_CATEGORIES.items():
        if any(word in query for word in keywords):
            issues.append(category)

    return issues
