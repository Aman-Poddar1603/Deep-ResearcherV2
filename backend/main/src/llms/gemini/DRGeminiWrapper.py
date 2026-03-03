from main.src.utils.DRLogger import dr_logger
from main.secrets.DRSecrets import Secrets
from google.genai import Client, types
from google.genai.types import ContentListUnionDict
from google.genai.types import Model
from typing import Literal, Optional, Generator
from main.src.utils.versionManagement import getAppVersion
from main.src.llms.prompts.getSchema import getImageUnderstandingSchema
from PIL import Image


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
        _log_googleai_event(
            "Gemini API key is missing.", level="error", urgency="critical"
        )
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
        _log_googleai_event(
            f"Gemini model '{model_name}' retrieved successfully.", level="success"
        )
        return model
    except ValueError as e:
        _log_googleai_event(str(e), level="error", urgency="critical")
        raise


def generateContent(
    prompt: str,
    system: str,
    model: str,
    image: Optional[str],
    client: Client,
) -> str:
    _log_googleai_event(f"Generating content with model: {model}")

    try:
        contents = []

        if image:
            contents.append(image)

        contents.append(prompt)

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(system_instruction=system),
        )

        _log_googleai_event("Content generated successfully.", level="success")

        if not response or not getattr(response, "text", None):
            _log_googleai_event(
                "Generated content is empty.",
                level="error",
                urgency="moderate",
            )
            raise ValueError("Generated content is empty.")

        return str(response.text).strip()

    except Exception as e:
        _log_googleai_event(
            f"Content generation failed: {e}",
            level="error",
            urgency="critical",
        )
        raise


def generateContentStream(
    prompt: str,
    system: str,
    model: str,
    image: Optional[str],
    client: Client,
) -> Generator[str, None, None]:
    _log_googleai_event(f"Starting streaming generation with model: {model}")

    try:
        contents = []

        if image:
            _log_googleai_event("Image content detected. Adding to stream payload.")
            contents.append(image)

        contents.append(prompt)

        _log_googleai_event(
            f"Prepared contents. Prompt length: {len(prompt)} chars.",
            level="info",
        )

        stream = client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(system_instruction=system),
        )

        _log_googleai_event("Stream connection established.", level="success")

        total_chunks = 0
        total_chars = 0

        for chunk in stream:
            total_chunks += 1

            if not chunk:
                _log_googleai_event(
                    f"Received empty chunk at index {total_chunks}.",
                    level="warning",
                )
                continue

            text = getattr(chunk, "text", None)

            if not text:
                _log_googleai_event(
                    f"Chunk {total_chunks} contained no text.",
                    level="warning",
                )
                continue

            total_chars += len(text)

            _log_googleai_event(
                f"Streaming chunk {total_chunks} ({len(text)} chars).",
                level="info",
            )

            yield text

        _log_googleai_event(
            f"Streaming completed successfully. "
            f"Total chunks: {total_chunks}, Total characters: {total_chars}.",
            level="success",
        )

    except Exception as e:
        _log_googleai_event(
            f"Streaming failed: {e}",
            level="error",
            urgency="critical",
        )
        raise


def understandImageWithoutSaving(
    image_path: str,
    prompt: str,
    system: str,
    model: str,
    client: Client,
) -> str:
    _log_googleai_event(f"Starting image understanding with model: {model}")

    try:
        # --- Read image ---
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        _log_googleai_event(
            f"Image loaded successfully. Size: {len(image_bytes)} bytes.",
            level="info",
        )

        # --- Build request ---
        response = client.models.generate_content(
            model=model,
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type="image/jpeg",  # change dynamically if needed
                ),
                prompt,
            ],
            config={
                "system_instruction": system,
                "response_mime_type": "application/json",
                "response_json_schema": getImageUnderstandingSchema(),
            },
        )

        _log_googleai_event(
            "Model processed image successfully.",
            level="success",
        )

        if not response or not getattr(response, "text", None):
            _log_googleai_event(
                "Image understanding response is empty.",
                level="error",
                urgency="moderate",
            )
            raise ValueError("Empty response from image understanding.")

        result_text = response.text.strip()

        _log_googleai_event(
            f"Generated description length: {len(result_text)} chars.",
            level="info",
        )

        # ---------------------------------------------------
        # 🔹 PLACEHOLDER: Upload image to storage bucket
        # Example:
        # bucket_url = upload_to_bucket(image_bytes)
        bucket_url = "BUCKET_UPLOAD_PLACEHOLDER"
        # ---------------------------------------------------

        # ---------------------------------------------------
        # 🔹 PLACEHOLDER: Save metadata + AI result to DB
        # Example:
        # save_image_analysis_to_db(
        #     image_path=image_path,
        #     bucket_url=bucket_url,
        #     ai_caption=result_text,
        #     model=model,
        # )
        db_record_id = "DB_SAVE_PLACEHOLDER"
        # ---------------------------------------------------

        _log_googleai_event(
            "Image analysis placeholders executed (DB + Bucket).",
            level="info",
        )

        return result_text

    except Exception as e:
        _log_googleai_event(
            f"Image understanding failed: {e}",
            level="error",
            urgency="critical",
        )
        raise


def understandImagesWithoutSaving(
    image_paths: list[str],
    prompt: str,
    system: str,
    model: str,
    client: Client,
) -> str:
    """
    Perform multi-image understanding using a Gemini model without persisting
    any files to long‑term storage.

    This helper mirrors `understandImageWithoutSaving` but supports multiple
    images in a single request. All images are loaded from disk, converted into
    Gemini `Part` objects, and sent alongside the textual prompt. The model is
    configured to return structured JSON using the image‑understanding schema.

    Parameters
    ----------
    image_paths:
        Ordered list of local filesystem paths to image files that should be
        analyzed together.
    prompt:
        The natural‑language instruction or question for the model (for
        example, asking for differences between the images or a combined
        description).
    system:
        System‑prompt string steering the model’s behavior (e.g. safety and
        formatting requirements).
    model:
        Gemini model name to use, such as ``\"gemini-3.1-pro\"`` or
        ``\"gemini-3-flash-preview\"``.
    client:
        Pre‑initialized ``google.genai.Client`` instance.

    Returns
    -------
    str
        The model’s textual response, typically JSON conforming to
        ``getImageUnderstandingSchema()``.

    Raises
    ------
    ValueError
        If no images are provided or the model returns an empty response.
    Exception
        Propagates any unexpected errors after logging them.
    """
    _log_googleai_event(
        f"Starting multi-image understanding with model: {model}"
    )

    try:
        if not image_paths:
            raise ValueError("At least one image path must be provided.")

        image_parts: list[ContentListUnionDict] = []

        for idx, image_path in enumerate(image_paths):
            with open(image_path, "rb") as f:
                image_bytes = f.read()

            _log_googleai_event(
                f"Loaded image {idx + 1}/{len(image_paths)} from '{image_path}' "
                f"({len(image_bytes)} bytes).",
                level="info",
            )

            # Try to infer a reasonable MIME type using Pillow; fall back to JPEG.
            try:
                with Image.open(image_path) as img:
                    mime_type = img.get_format_mimetype() or "image/jpeg"
            except Exception:
                mime_type = "image/jpeg"

            image_parts.append(
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type,
                )
            )

        contents: list[ContentListUnionDict] = [
            *image_parts,
            prompt,
        ]

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config={
                "system_instruction": system,
                "response_mime_type": "application/json",
                "response_json_schema": getImageUnderstandingSchema(),
            },
        )

        _log_googleai_event(
            "Model processed multi-image request successfully.",
            level="success",
        )

        if not response or not getattr(response, "text", None):
            _log_googleai_event(
                "Multi-image understanding response is empty.",
                level="error",
                urgency="moderate",
            )
            raise ValueError("Empty response from multi-image understanding.")

        result_text = response.text.strip()

        _log_googleai_event(
            f"Generated multi-image description length: {len(result_text)} chars.",
            level="info",
        )

        return result_text

    except Exception as e:
        _log_googleai_event(
            f"Multi-image understanding failed: {e}",
            level="error",
            urgency="critical",
        )
        raise




# client = getClient()

# with open("./gemini_models.txt", "w") as f:
#     f.write(str(getGeminiModel(client=client, model_name="gemini-2.0-flash-lite")))
