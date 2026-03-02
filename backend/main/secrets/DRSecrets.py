"""
## Module: DRSecrets

### Description

Manages secure secret and API key management for the Deep Researcher application.
This module is responsible for loading environment variables from a .env file,
providing secure access to API keys with proper logging and fallback resolution
for multiple API key sources (e.g., Gemini API keys).

### Key Components

- **Secrets class**: Main interface for accessing and managing API keys
- **_log_secret_event function**: Internal logging utility for secret operations

### Usage Example

```python
from main.secrets.DRSecrets import Secrets

secrets = Secrets()
gemini_key = secrets.get_gemini_api_key()
generic_key = secrets.get_secret("CUSTOM_API_KEY")
```

### Dependencies

- `python-dotenv`: For loading environment variables from .env files
- `DRLogger`: Custom logging utility for structured event logging
- `versionManagement`: Provides application version information
"""

from dotenv import dotenv_values
from pathlib import Path
from main.src.utils.DRLogger import DRLogger
from main.src.utils.versionManagement import getAppVersion
from typing import Literal


LOG_SOURCE = "system"
LOG_TAGS = ["SECRETS_MANAGEMENT"]

logger: DRLogger = DRLogger()
DIR = Path(__file__).parent


def _log_secret_event(
    level: Literal["success", "error", "warning", "info"],
    message: str,
    urgency: Literal["none", "moderate", "critical"] = "none",
):
    """
    ## Description

    Internal utility function for logging secret management events with structured
    metadata. Ensures all secret-related operations are tracked with appropriate
    urgency levels and log sources.

    ## Parameters

    - `level` (`Literal["success", "error", "warning", "info"]`)
      - Description: Log severity level indicating the nature of the event.
      - Constraints: Must be one of: "success", "error", "warning", "info".
      - Example: "error"

    - `message` (`str`)
      - Description: Human-readable description of the secret event.
      - Constraints: Must be non-empty. Should not contain sensitive data (API keys, tokens).
      - Example: ".env file not found at /path/to/.env"

    - `urgency` (`Literal["none", "moderate", "critical"]`, optional)
      - Description: Priority indicator for the logged event.
      - Constraints: Must be one of: "none", "moderate", "critical".
      - Default: "none"
      - Example: "critical"

    ## Returns

    `None`

    ## Side Effects

    - Writes log entry to the DRLogger system.
    - Includes application version in all log entries.
    - Tags all events with "SECRETS_MANAGEMENT" for filtering.

    ## Debug Notes

    - Ensure messages do NOT contain sensitive information (API keys, tokens).
    - Use appropriate urgency levels: "critical" for missing keys, "moderate" for fallbacks.
    - Check logger output in application logs directory.

    ## Customization

    To change log source or tags globally, modify the module-level constants:
    - `LOG_SOURCE`: Change from "system" to custom value
    - `LOG_TAGS`: Extend list with additional tags
    """
    logger.log(
        level,
        message,
        LOG_SOURCE,
        LOG_TAGS,
        urgency,
        app_version=getAppVersion(),
    )


class Secrets:
    """
    ## Description

    Manages secure API key and environment variable access for the Deep Researcher
    application. Loads secrets from a .env file during initialization and provides
    secure methods to retrieve API keys with fallback resolution for multiple sources.
    All access attempts are logged for audit and debugging purposes.

    ## Initialization

    Upon instantiation, searches for a .env file in the `env/` subdirectory of the
    module location. If not found, raises `FileNotFoundError` with critical urgency.
    Successfully loaded keys are stored in the `API_KEYS` dictionary.

    ## Usage Example

    ```python
    secrets = Secrets()
    gemini_api = secrets.get_gemini_api_key()  # Tries multiple fallback keys
    custom_api = secrets.get_secret("CUSTOM_KEY_NAME")
    ```

    ## Attributes

    - `API_KEYS` (`dict[str, str]`)
      - Description: Dictionary containing all loaded environment variables from .env file.
      - Populated during `__init__`.
      - Keys correspond to variable names in .env file.

    ## Error Handling

    - Missing .env file: Raises `FileNotFoundError` during initialization.
    - Missing specific key: Methods return `None` and log with critical urgency.
    - All exceptions are caught and logged before re-raising or returning None.
    """

    def __init__(self):
        """
        ## Description

        Initializes the Secrets manager by loading environment variables from a .env file.
        The .env file is expected to be located in the `env/` subdirectory relative to
        this module. All loaded keys are stored in the `API_KEYS` instance attribute.

        ## Parameters

        None

        ## Returns

        `None`

        ## Raises

        - `FileNotFoundError`
          - When .env file is not found at the expected location.
          - Location: `{module_dir}/env/.env`

        - `Exception`
          - Any exception from dotenv_values() or file system operations is caught, logged, and re-raised.

        ## Side Effects

        - Loads all variables from .env file into `self.API_KEYS` dictionary.
        - Logs initialization steps (info level for each step, success on completion).
        - Critical error logging if .env file is missing or loading fails.

        ## Debug Notes

        - Required .env file location: `main/secrets/env/.env`
        - Check logs for "Successfully loaded environment variables" message.
        - If missing, ensure .env file exists in the correct directory.
        - The .env file should never be committed to version control.

        ## Customization

        To change the .env file location, modify the path construction:
        ```python
        env_pth = DIR / "env" / ".env"  # Current
        # Change to:
        env_pth = DIR / "custom_dir" / ".env"  # Custom location
        ```
        """
        self.API_KEYS = {}

        try:
            _log_secret_event("info", "Finding the .env file.", "none")

            env_pth = DIR / "env" / ".env"

            if not env_pth.exists():
                _log_secret_event(
                    "error",
                    f".env file not found at {env_pth}.",
                    "critical",
                )
                raise FileNotFoundError(f"Missing .env at {env_pth}")

            _log_secret_event(
                "info",
                "Loading environment variables from .env file.",
                "none",
            )

            self.API_KEYS = dotenv_values(env_pth)

            _log_secret_event(
                "success",
                "Successfully loaded environment variables.",
                "none",
            )

        except Exception as e:
            _log_secret_event(
                "error",
                f"Failed to initialize Secrets. Error: {str(e)}",
                "critical",
            )
            raise

    # -------------------------
    # Generic Secret Getter
    # -------------------------
    def get_secret(self, key_name: str):
        """
        ## Description

        Generic method to retrieve any environment variable/secret from the loaded .env file.
        Returns the value if found, otherwise logs an error and returns None.
        All access attempts are logged for audit purposes.

        ## Parameters

        - `key_name` (`str`)
          - Description: The name of the environment variable to retrieve.
          - Constraints: Must be non-empty and match the exact key name in .env file (case-sensitive).
          - Example: "CUSTOM_API_KEY" or "DATABASE_URL"

        ## Returns

        `str | None`

        - Returns the secret value if found and non-empty.
        - Returns `None` if key is not found or value is empty.

        ## Raises

        - `Exception`
          - Any exception during dictionary lookup is caught, logged, and returns None.

        ## Side Effects

        - Logs successful retrieval at success level.
        - Logs missing/empty key at error level with critical urgency.
        - Logs any exceptions at error level with critical urgency.

        ## Debug Notes

        - Ensure key name matches exactly (case-sensitive) with .env variable name.
        - Check logger output if return value is None.
        - Empty string values are treated as missing keys.

        ## Customization

        To handle missing keys differently (raise exception instead of returning None):
        ```python
        if value is None:
            raise KeyError(f"Secret '{key_name}' not found in environment")
        ```
        """
        try:
            _log_secret_event(
                "info",
                f"Attempting to fetch {key_name}.",
                "none",
            )

            value = self.API_KEYS.get(key_name)

            if value:
                _log_secret_event(
                    "success",
                    f"{key_name} loaded successfully.",
                    "none",
                )
                return value

            _log_secret_event(
                "error",
                f"{key_name} not found or empty.",
                "critical",
            )
            return None

        except Exception as e:
            _log_secret_event(
                "error",
                f"Exception while fetching {key_name}. Error: {str(e)}",
                "critical",
            )
            return None

    # -------------------------
    # Gemini Fallback Resolver
    # -------------------------
    def get_gemini_api_key(self):
        """
        ## Description

        Retrieves a valid Gemini API key using a fallback resolution strategy.
        Attempts to load keys in order: GEMINI_API_KEY_1, GEMINI_API_KEY_2, GEMINI_API_KEY_3.
        Returns the first available key found. If all keys are missing, returns None.
        Each attempt is logged with appropriate status (success or warning for fallback).

        ## Parameters

        None

        ## Returns

        `str | None`

        - Returns the first available Gemini API key value.
        - Returns `None` if all three API keys are missing or empty.

        ## Raises

        - `Exception`
          - Any exception during key resolution is caught, logged, and returns None.

        ## Side Effects

        - Logs each attempted key name at info level.
        - Logs success at success level when a key is found.
        - Logs warnings at moderate urgency for each failed fallback attempt.
        - Logs final error at critical urgency if all keys fail.

        ## Debug Notes

        - Fallback order is hardcoded: GEMINI_API_KEY_1 → GEMINI_API_KEY_2 → GEMINI_API_KEY_3
        - Check logs to see which key was successfully loaded.
        - If all keys return None, verify .env file contains at least one GEMINI_API_KEY_* entry.
        - Ensure API keys are not empty strings in .env file.

        ## Customization

        To add more fallback keys or change the order:
        ```python
        gemini_keys = (
            "GEMINI_API_KEY_1",
            "GEMINI_API_KEY_2",
            "GEMINI_API_KEY_3",
            "GEMINI_API_KEY_4",  # Add new key
        )
        ```

        To use a different key naming scheme:
        ```python
        gemini_keys = ("GEMINI_PRIMARY", "GEMINI_BACKUP")  # Custom names
        ```
        """
        try:
            gemini_keys = (
                "GEMINI_API_KEY_1",
                "GEMINI_API_KEY_2",
                "GEMINI_API_KEY_3",
            )

            for key_name in gemini_keys:
                _log_secret_event(
                    "info",
                    f"Attempting to fetch {key_name}.",
                    "none",
                )

                api_key = self.API_KEYS.get(key_name)

                if api_key:
                    _log_secret_event(
                        "success",
                        f"{key_name} loaded successfully.",
                        "none",
                    )
                    return api_key

                _log_secret_event(
                    "warning",
                    f"{key_name} not available. Trying next fallback.",
                    "moderate",
                )

            _log_secret_event(
                "error",
                "All Gemini API keys failed to load.",
                "critical",
            )
            return None

        except Exception as e:
            _log_secret_event(
                "error",
                f"Exception while resolving Gemini API key. Error: {str(e)}",
                "critical",
            )
            return None
