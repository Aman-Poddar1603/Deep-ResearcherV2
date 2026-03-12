# Default File Scoped utility functions
import datetime


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)

def utcnow_iso() -> str:
    return utcnow().isoformat()



# String utilities

def checkStringIsEmpty(s: str) -> bool:
    return s is None or s.strip() == ""

def convertExplicitToString(s: str) -> str:
    if s is None:
        return ""
    return s.strip()