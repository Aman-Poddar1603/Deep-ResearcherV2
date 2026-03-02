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
    logger.log(
        level,
        message,
        LOG_SOURCE,
        LOG_TAGS,
        urgency,
        app_version=getAppVersion(),
    )


class Secrets:
    def __init__(self):
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
