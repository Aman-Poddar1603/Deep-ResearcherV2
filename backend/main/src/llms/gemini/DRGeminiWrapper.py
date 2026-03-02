from main.src.utils.DRLogger import dr_logger
from main.secrets.DRSecrets import Secrets
from google.genai import Client
from google.genai.types import Model
from typing import Literal
from main.src.utils.versionManagement import getAppVersion




LOG_SOURCE = "system"
LOG_TAGS = ["SECRETS_MANAGEMENT"]


def _log_googleai_event(
    message: str,
    level: Literal["success", "error", "warning", "info"] = "info",
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
    dr_logger.log(
        log_type=level,
        message=message,
        origin=LOG_SOURCE,
        urgency=urgency,
        module="API",
        app_version=getAppVersion(),
    )


def getClient():
    _log_googleai_event("Initializing Gemini Client")
    secrets = Secrets()
    api_key = secrets.get_gemini_api_key()
    if not api_key:
        _log_googleai_event("Gemini API key is missing.", level="error", urgency="critical")
        raise ValueError("Gemini API key is missing.")
    try:
        _log_googleai_event("Attempt to create Gemini Client.")
        client = Client(api_key=api_key)
        _log_googleai_event("Gemini Client initialized successfully.", level="success")
    except ValueError as e:
        _log_googleai_event(str(e), level="error", urgency="critical")
        raise
    return client


def getModelList(client: Client) -> list[dict]:
    _log_googleai_event("Retrieving list of available Gemini models.")

    try:
        model_list = client.models.list()

        parsed_models = []

        for model in model_list:
            try:
                model_dict = model.model_dump()  # modern pydantic way
            except AttributeError:
                model_dict = model.__dict__  # fallback safety

            parsed_models.append(model_dict)

        _log_googleai_event(
            f"Retrieved {len(parsed_models)} models successfully.",
            level="success",
        )

        return parsed_models

    except Exception as e:
        _log_googleai_event(
            str(e),
            level="error",
            urgency="critical",
        )
        raise


def getGeminiModel(client: Client, model_name: str = "gemini-3.1-pro") -> Model:
    _log_googleai_event(f"Retrieving Gemini model: {model_name}")
    try:
        model = client.models.get(model=model_name)
        _log_googleai_event(f"Gemini model '{model_name}' retrieved successfully.", level="success")
        return model
    except ValueError as e:
        _log_googleai_event(str(e), level="error", urgency="critical")
        raise


def generateContent()

# client = getClient()

# with open("./gemini_models.txt", "w") as f:
#     f.write(str(getGeminiModel(client=client, model_name="gemini-2.0-flash-lite")))
