import json
import logging
from typing import Any, Optional, TypedDict

from google.genai import Client
from pydantic import BaseModel, Field

from query.LLMPreProcessStrategy import validateQuery

SYSTEM_PROMPT: str = """
You are a high-precision research summarization agent.

Your task is to generate a concise and relevant summary of given content based strictly on the provided query.

## OBJECTIVE
Extract the most important and query-relevant information from the content.

## STRICT RULES
- The summary MUST be under 200 words.
- Focus ONLY on information relevant to the query.
- Prioritize key facts, insights, and conclusions.
- Remove noise, redundancy, and unrelated details.
- Do NOT hallucinate or invent information.
- If relevant information is missing, return:
  "Insufficient relevant information found."

## OUTPUT FORMAT (MANDATORY)
Return a valid JSON object matching this schema:

{
  "query": "<original query>",
  "summary": "<final summarized answer>"
}

## CONSTRAINTS
- Do not add extra keys.
- Do not include explanations or metadata.
- Ensure the JSON is valid and properly formatted.
"""


class SummarizerAgent(BaseModel):
    query: str = Field(..., description="This is the raw query text to be summarized.")
    summary: str = Field(..., description="The summarized text output.")


class SummarizerResult(TypedDict):
    query: str
    summary: str


def _extract_candidate_text(response: Any) -> Optional[Any]:
    candidates = getattr(response, "candidates", None)
    if not isinstance(candidates, list) or not candidates:
        return None

    content = getattr(candidates[0], "content", None)
    if content is None:
        return None

    parts = getattr(content, "parts", None)
    if not isinstance(parts, list) or not parts:
        return None

    return getattr(parts[0], "text", None)


def summarize(query: str, api_key: str) -> SummarizerResult:
    try:
        validated_query = validateQuery(query=query, api_key=api_key)
        safe_prompt = validated_query.get("safe_prompt")

        if not isinstance(safe_prompt, str) or not safe_prompt.strip():
            return {
                "query": query,
                "summary": "Insufficient relevant information found.",
            }

        try:
            response = Client(api_key=api_key).models.generate_content(
                model="gemini-3-flash-preview",
                contents=safe_prompt,
                config={
                    "system_instruction": SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                    "response_json_schema": SummarizerAgent.model_json_schema(),
                },
            )

            text = getattr(response, "text", None)

            if isinstance(text, str) and text.strip():
                validated = SummarizerAgent.model_validate_json(text)
                return {
                    "query": validated.query,
                    "summary": validated.summary,
                }

            # fallback parsing
            part_text = _extract_candidate_text(response)

            if isinstance(part_text, str) and part_text.strip():
                obj = json.loads(part_text)
            elif part_text is not None:
                obj = part_text
            else:
                raise ValueError("Model response did not contain parseable text")

            validated = SummarizerAgent.model_validate(obj)
            return {
                "query": validated.query,
                "summary": validated.summary,
            }

        except Exception as e:
            logging.debug("LLM failed: %s", e)

            # -------------------------------
            # 🛡️ LAYER 3: FAILSAFE MODE
            # -------------------------------
            return {
                "query": query,
                "summary": safe_prompt,
            }
    except Exception as e:
        raise e
