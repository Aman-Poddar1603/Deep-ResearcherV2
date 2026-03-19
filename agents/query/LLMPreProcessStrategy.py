import json
import logging
from typing import Any, List, Optional

from google.genai import Client
from pydantic import BaseModel, Field, ValidationError

from query.query_preprocess import query_preprocessor
from query.safety import detect_prompt_injection, detect_safety_issues


class StructuredQuery(BaseModel):
    query: str = Field(
        ..., description="This will be the user's query to be processed by the You."
    )
    is_safe: bool = Field(
        ...,
        description="This will be a boolean indicating whether the query is safe to execute.",
    )
    issue: List[str] = Field(
        ...,
        description="This will be a list of issues found in the query otherwise leave it empty.",
    )
    # OPTIONAL: include these if you expect them in the model_json_schema()
    summary: Optional[str] = Field(None, description="<=100 word summary of the query.")
    safe_prompt: Optional[str] = Field(None, description="Sanitized prompt or null.")


def _compact_repr(x: Any, max_len: int = 400) -> str:
    try:
        r = repr(x)
    except Exception:
        return "<unrepresentable>"
    if len(r) > max_len:
        return r[: max_len - 3] + "..."
    return r


def validateQuery(system_prompt: str, query: str, api_key: str) -> dict:
    alphabetical_safe_query = query_preprocessor.preprocess(query)
    clean_query = alphabetical_safe_query["for_pcd"]

    # -------------------------------
    # ⚡ LAYER 1: HARD FILTERS
    # -------------------------------
    issues = []

    if detect_prompt_injection(clean_query):
        issues.append("prompt_injection")

    safety_issues = detect_safety_issues(clean_query)
    issues.extend(safety_issues)

    is_safe = len(issues) == 0

    # 🚫 If clearly unsafe → no LLM call
    if not is_safe:
        return {
            "query": clean_query,
            "is_safe": False,
            "issue": issues,
            "summary": clean_query[:100],
            "safe_prompt": None,
        }

    # -------------------------------
    # 🧠 LAYER 2: LLM ENHANCEMENT
    # -------------------------------
    client = Client(api_key=api_key)
    response = None

    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=clean_query,
            config={
                "system_instruction": system_prompt,
                "response_mime_type": "application/json",
                "response_json_schema": StructuredQuery.model_json_schema(),
            },
        )

        text = getattr(response, "text", None)

        if isinstance(text, str) and text.strip():
            validated = StructuredQuery.model_validate_json(text)
            return validated.model_dump()

        # fallback parsing
        part_text = response.candidates[0].content.parts[0].text

        if isinstance(part_text, str):
            obj = json.loads(part_text)
        else:
            obj = part_text

        validated = StructuredQuery.model_validate(obj)
        return validated.model_dump()

    except Exception as e:
        logging.debug("LLM failed: %s", e)

        # -------------------------------
        # 🛡️ LAYER 3: FAILSAFE MODE
        # -------------------------------
        return {
            "query": clean_query,
            "is_safe": True,
            "issue": [],
            "summary": clean_query[:100],
            "safe_prompt": f"Answer safely: {clean_query}",
        }
