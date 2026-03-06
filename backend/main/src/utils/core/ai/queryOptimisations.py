from typing import Literal
from main.src.utils.DRLogger import dr_logger
from main.src.utils.version_constants import get_raw_version
from main.src.utils.llms.gemini.DRGeminiWrapper import (
    Client
)


LOG_SOURCE = "system"  # Constant for log source identification


def _log_quiery_optimisation(
    message: str,
    level: Literal["success", "error", "warning", "info"] = "info",
    urgency: Literal["none", "moderate", "critical"] = "none",
):
    """
    ## Description

    Internal utility function for logging image embedding events with structured
    metadata. Ensures all embedding-related operations are tracked with appropriate
    urgency levels and log sources.

    ## Parameters

    - `message` (`str`)
      - Description: Human-readable description of the image embedding event.
      - Constraints: Must be non-empty.
      - Example: "ONNX session initialized successfully."

    - `level` (`Literal["success", "error", "warning", "info"]`, optional)
      - Description: Log severity level indicating the nature of the event.
      - Constraints: Must be one of: "success", "error", "warning", "info".
      - Default: "info"
      - Example: "error"

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
    - Routes logs to the "UTILS" module table.

    ## Debug Notes

    - Use appropriate urgency levels: "critical" for model loading failures,
      "moderate" for non-fatal warnings.
    - Check logger output in the `utils_logs` table.

    ## Customization

    To change log source globally, modify the module-level constant:
    - `LOG_SOURCE`: Change from "system" to custom value.
    """
    dr_logger.log(
        log_type=level,
        message=message,
        origin=LOG_SOURCE,
        urgency=urgency,
        module=[
            "UTILS",
            "AGENTS",
            
        ],  # Logs from this function are categorized under the "UTILS" module
        app_version=get_raw_version(),
    )
