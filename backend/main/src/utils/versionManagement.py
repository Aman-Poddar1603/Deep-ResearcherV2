from main.src.store.DBManager import main_db_manager, SQLiteManager
from main.src.utils.DRLogger import DRLogger
from typing import Literal
import uuid

MAJOR_CHANGE = 2

NEW_FEATURE = 0
MINOR_BUGFIXES = 1

# Constants for logging - easier to maintain
LOG_SOURCE = "system"
LOG_TAGS = ["VERSION_MANAGEMENT"]


def _get_version():
    return f"{MAJOR_CHANGE}.{NEW_FEATURE}.{MINOR_BUGFIXES}"


dbmgr: SQLiteManager = main_db_manager
logger: DRLogger = DRLogger()


def _log_version_event(
    level: Literal["success", "error", "warning", "info"],
    message: str,
    urgency: Literal["none", "moderate", "critical"] = "none",
):
    """Helper function to reduce logging boilerplate"""
    logger.log(
        level,
        message,
        LOG_SOURCE,
        LOG_TAGS,
        urgency,
        app_version=_get_version(),
    )


def _logToVersionHistoryTable():
    try:
        _log_version_event("info", "Fetching version history from the database.")

        version_history = dbmgr.create_table(
            "version_history",
            {
                "id": "TEXT PRIMARY KEY UNIQUE",
                "version": "TEXT NOT NULL UNIQUE",
                "changes": "TEXT NOT NULL",
                "last_updated": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            },
        )

        _log_version_event(
            "success",
            version_history.get("message") or "Version history table is created.",
            "critical" if version_history.get("success") else "none",
        )

        try:
            # Check if version already exists
            existing_version = dbmgr.fetch_one(
                "version_history", where={"version": _get_version()}
            )

            if existing_version.get("success") and existing_version.get("data"):
                _log_version_event(
                    "info",
                    f"Version {_get_version()} already exists in history",
                )
            else:
                _log_version_event(
                    "info",
                    "Logging the version in the version history.",
                )

                # Insert only if version doesn't exist
                insert_result = dbmgr.insert(
                    "version_history",
                    {
                        "id": str(uuid.uuid4()),
                        "version": _get_version(),
                        "changes": "Initial release with major changes.",
                    },
                )

                if insert_result.get("success"):
                    _log_version_event(
                        "success",
                        f"Version {_get_version()} logged to history",
                        "critical",
                    )
                else:
                    _log_version_event(
                        "error",
                        f"Failed to log version: {insert_result.get('message')}",
                        "critical",
                    )

        except Exception as e:
            _log_version_event(
                "error",
                f"Error while logging version history: {e}",
                "critical",
            )
        return version_history
    except Exception as e:
        _log_version_event(
            "error",
            f"Error while fetching version history: {e}",
            "critical",
        )
        return []


def getAppVersion():
    """Public function to get the current app version"""
    try:
        _log_version_event("info", "Retrieving application version.")
        _logToVersionHistoryTable()
        _log_version_event("success", "Successfully retrieved application version.")
    except Exception as e:
        _log_version_event(
            "error",
            f"Error in getAppVersion: {e}",
            "critical",
        )
    return _get_version()


def setAppVersion(major: int, feature: int, minor: int, changes: str):
    """Public function to set the application version - for future use when we implement dynamic versioning"""
    global MAJOR_CHANGE, NEW_FEATURE, MINOR_BUGFIXES
    try:
        _log_version_event("info", "Setting application version.")
        MAJOR_CHANGE = major
        NEW_FEATURE = feature
        MINOR_BUGFIXES = minor
        _log_version_event(
            "success",
            f"Application version set to {MAJOR_CHANGE}.{NEW_FEATURE}.{MINOR_BUGFIXES}",
            "critical",
        )
    except Exception as e:
        _log_version_event(
            "error",
            f"Error in setAppVersion: {e}",
            "critical",
        )


def updateVersionHistory(changes: str, version: str = _get_version()):
    """Public function to update the version history with new changes - for future use when we implement dynamic versioning"""
    try:
        _log_version_event("info", "Updating version history with new changes.")
        result = dbmgr.update(
            "version_history",
            {"changes": changes, "last_updated": "CURRENT_TIMESTAMP"},
            where={"version": _get_version()},
        )
        if result.get("success"):
            _log_version_event(
                "success",
                f"Version history updated for version {_get_version()}",
                "critical",
            )
        else:
            _log_version_event(
                "error",
                f"Failed to update version history: {result.get('message')}",
                "critical",
            )
    except Exception as e:
        _log_version_event(
            "error",
            f"Error in updateVersionHistory: {e}",
            "critical",
        )
