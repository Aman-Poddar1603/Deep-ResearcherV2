---
name: gemini-wrapper
description: Conventions for using the Gemini (google-genai) wrapper, logging, and async APIs in this backend.
---

## Gemini Wrapper Conventions

- Use `main.src.llms.gemini.DRGeminiWrapper` as the single integration point for Google Gen AI.
- Prefer **async** helpers for new code:
  - `getAsyncClient()` for the async client instance (`Client().aio`).
  - `asyncGenerateContent`, `asyncGenerateContentStream` for text and streaming.
  - `asyncGenerateWithTools` for robust tool/function calling.
  - `asyncGenerateImageArtifact` when an “artifact” (e.g., image) is required.

## Logging Requirements

- Always log via `_log_googleai_event` in this module instead of calling `dr_logger` directly.
- Log:
  - Start/end of any public helper.
  - All external calls (Gemini, file IO) with enough context to debug crashes.
  - Failures with `level="error"` and `urgency="critical"` where behavior degrades.
- Do **not** include secrets (API keys, tokens, raw env values) in log messages.

## Tool Calling

- For new tool/function-calling flows with Gemini:
  - Reuse `asyncGenerateWithTools` and pass `automatic_mode`:
    - `"AUTO"` – default automatic behavior.
    - `"ANY"` – model always returns function calls.
    - `"NONE"` – tools attached, automatic function calling disabled.
  - Let callers inspect `response.function_calls` when they need manual control.

## Artifacts

- “Artifacts” (e.g., generated images) should go through `asyncGenerateImageArtifact` unless there is a strong reason to bypass it.
- This helper uses the Interactions API with `response_modalities=['IMAGE']`; callers are responsible for persisting or serving binary data.

## General Rules

- Do **not** duplicate Gemini client initialization elsewhere; call `getClient()` or `getAsyncClient()`.
- Favor small, composable helpers in this module over ad-hoc calls scattered across the codebase.
- Keep new helpers under ~150 lines, with docstrings explaining:
  - Purpose.
  - Parameters.
  - Return types.
  - Failure/edge-case behavior.

