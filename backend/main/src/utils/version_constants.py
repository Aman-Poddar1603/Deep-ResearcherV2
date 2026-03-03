"""
Core version constants for the application.
Decoupled from logic/logging to prevent circular imports.
"""

MAJOR_CHANGE = 2
NEW_FEATURE = 0
MINOR_BUGFIXES = 1

def get_raw_version() -> str:
    """Returns the version string without any side effects or logging."""
    return f"{MAJOR_CHANGE}.{NEW_FEATURE}.{MINOR_BUGFIXES}"
