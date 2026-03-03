# GEMINI

This directory contains the **Gemini (Google Gen AI) integration** for the Deep Researcher backend.
All direct interaction with the `google-genai` SDK should go through the wrapper module:

- `main/src/llms/gemini/DRGeminiWrapper.py`

This keeps the integration **modular, reusable, and future‑proof**, so you can plug it into
multiple services (REST API, agents, background workers) without duplicating logic.

> There will be a separate **OLLAMA** section in the future; for now this README focuses
> solely on the Gemini integration.

---

### 1. Overview of `DRGeminiWrapper`

The wrapper centralizes:

- **Client creation** (sync + async) using `google-genai`.
- **Text generation** (single-shot and streaming).
- **Tool / function calling** helpers.
- **Multimodal image understanding** (single and multi-image).
- **Artifact generation** (e.g. image artifacts via Interactions).
- **Consistent logging** of every important event via `_log_googleai_event`.

You should not call `google.genai.Client` directly in other modules; instead, import and use
these functions from `DRGeminiWrapper`.

---

### 2. Client Initialization

#### 2.1 Sync client

Use when you are in synchronous code (e.g. simple scripts or sync endpoints):

```python
from main.src.llms.gemini.DRGeminiWrapper import getClient

client = getClient()
```

Behavior:
- Reads Gemini API key(s) from `Secrets` (see `main/secrets/DRSecrets.py`).
- Logs initialization steps and failures via `_log_googleai_event`.
- Raises `ValueError` if no API key is available.

#### 2.2 Async client

Preferred for web handlers / high-concurrency scenarios:

```python
from main.src.llms.gemini.DRGeminiWrapper import getAsyncClient

aclient = getAsyncClient()  # this is Client(api_key=...).aio
```

Use this in frameworks like FastAPI, Starlette, etc., where you want to `await` Gemini calls.

---

### 3. Text Generation

#### 3.1 Sync `generateContent`

```python
from main.src.llms.gemini.DRGeminiWrapper import getClient, generateContent

client = getClient()
text = generateContent(
    prompt="Explain vector databases in simple terms.",
    system="You are a concise technical explainer.",
    model="gemini-3.1-pro",
    image=None,
    client=client,
)
```

Key points:
- Accepts optional `image` (string identifier) which is appended before the prompt.
- Uses `types.GenerateContentConfig(system_instruction=system)` under the hood.
- Logs start, success, and error conditions; raises if response is empty.

#### 3.2 Sync streaming `generateContentStream`

```python
from main.src.llms.gemini.DRGeminiWrapper import getClient, generateContentStream

client = getClient()

for chunk in generateContentStream(
    prompt="Stream a 300-word story.",
    system="You are a storyteller.",
    model="gemini-3.1-pro",
    image=None,
    client=client,
):
    print(chunk, end="", flush=True)
```

Key points:
- Uses `client.models.generate_content_stream(...)`.
- Logs each chunk, including counts and final stats.

---

### 4. Async Text Generation

#### 4.1 `asyncGenerateContent`

```python
from main.src.llms.gemini.DRGeminiWrapper import getAsyncClient, asyncGenerateContent

aclient = getAsyncClient()

text = await asyncGenerateContent(
    prompt="Summarize this in three bullet points.",
    system="You are a summarization assistant.",
    model="gemini-3.1-pro",
    image=None,
    aclient=aclient,
)
```

Optional parameters:
- `tools`: list of tools / Python functions / `types.Tool` objects.
- `json_schema`: JSON schema dict for structured JSON output
  (sets `response_mime_type='application/json'` and `response_json_schema` internally).

#### 4.2 `asyncGenerateContentStream`

```python
from main.src.llms.gemini.DRGeminiWrapper import getAsyncClient, asyncGenerateContentStream

aclient = getAsyncClient()

async for chunk in asyncGenerateContentStream(
    prompt="Stream a long response.",
    system="You are a detailed assistant.",
    model="gemini-3.1-pro",
    image=None,
    aclient=aclient,
):
    yield chunk  # or write to WebSocket / HTTP stream
```

Use this in async endpoints when you want incremental tokens for multiple users at once.

---

### 5. Tool / Function Calling

#### 5.1 `asyncGenerateWithTools`

High-level helper for tool-calling patterns:

```python
from main.src.llms.gemini.DRGeminiWrapper import (
    getAsyncClient,
    asyncGenerateWithTools,
)
from google.genai import types

aclient = getAsyncClient()

def get_weather(location: str) -> str:
    return "sunny"

response = await asyncGenerateWithTools(
    prompt="What is the weather in Boston?",
    system="You are a weather assistant.",
    model="gemini-3.1-pro",
    aclient=aclient,
    tools=[get_weather],
    automatic_mode="AUTO",  # or "ANY" / "NONE"
)
```

Modes:
- `"AUTO"` – default automatic function calling.
- `"ANY"` – model always returns function calls (no auto-execution).
- `"NONE"` – attach tools, but disable automatic function calling.

Inspect:
- `response.text` for plain answers.
- `response.function_calls` when you want to manually run tools and send results back.

---

### 6. Models and Metadata

#### 6.1 `getModelList`

```python
from main.src.llms.gemini.DRGeminiWrapper import getClient, getModelList

client = getClient()
models = getModelList(client)
```

Returns:
- A `list[dict]` of models, converted via `.model_dump()` when available,
  or `__dict__` as a fallback. Useful for UI dropdowns or diagnostics.

#### 6.2 `getGeminiModel`

```python
from main.src.llms.gemini.DRGeminiWrapper import getClient, getGeminiModel

client = getClient()
model_info = getGeminiModel(client, model_name="gemini-3.1-pro")
```

Returns:
- A `Model` object from `google.genai.types`, with logging and error handling.

---

### 7. Image Understanding

#### 7.1 Single image: `understandImageWithoutSaving`

```python
from main.src.llms.gemini.DRGeminiWrapper import (
    getClient,
    understandImageWithoutSaving,
)

client = getClient()

result = understandImageWithoutSaving(
    image_path="/path/to/image.jpg",
    prompt="Describe this image in detail.",
    system="You are an image analysis assistant.",
    model="gemini-3.1-pro",
    client=client,
)
```

Behavior:
- Reads the image bytes from disk.
- Sends `types.Part.from_bytes(...)` plus the prompt.
- Uses `getImageUnderstandingSchema()` to request structured JSON output.
- Contains placeholders where you can later plug in bucket / DB persistence.

#### 7.2 Multi-image: `understandImagesWithoutSaving`

```python
from main.src.llms.gemini.DRGeminiWrapper import (
    getClient,
    understandImagesWithoutSaving,
)

client = getClient()

result = understandImagesWithoutSaving(
    image_paths=["/img/one.jpg", "/img/two.jpg"],
    prompt="Compare these two images.",
    system="You are a comparison assistant.",
    model="gemini-3.1-pro",
    client=client,
)
```

Behavior:
- Loads each image, infers MIME type via Pillow, and sends them with the prompt.
- Uses the same JSON schema as the single-image helper.

---

### 8. Artifact Generation (Images via Interactions)

#### 8.1 `asyncGenerateImageArtifact`

```python
from main.src.llms.gemini.DRGeminiWrapper import (
    getAsyncClient,
    asyncGenerateImageArtifact,
)

aclient = getAsyncClient()

artifact = await asyncGenerateImageArtifact(
    prompt="Generate an infographic about vector databases.",
    model="gemini-3-pro-image-preview",
    aclient=aclient,
)

if artifact:
    mime_type = artifact["mime_type"]
    data_b64 = artifact["data"]
    # Caller is responsible for decoding and persisting/serving the image bytes.
```

This uses the **Interactions API** with `response_modalities=['IMAGE']` and returns
a small dict with metadata; persistence and delivery are handled by the caller.

---

### 9. Logging & Debugging

All helper functions log via the internal `_log_googleai_event`:

- Every major start/end event.
- External calls (Gemini, file IO).
- Errors at `level="error"` with `urgency="critical"` when behavior degrades.

If the app crashes or behaves unexpectedly, you can inspect logs (via `DRLogger`)
to reconstruct what the Gemini integration was doing at the time.

---

### 10. Design Principles

- **Modular**: All Gemini logic lives in `DRGeminiWrapper`, so it can be reused by
  multiple modules and services.
- **Async-first**: New integrations should prefer the async helpers for scalability.
- **Extensible**: Additional capabilities (e.g. Redis-based resumable streams,
  Ollama integration) should be implemented in separate modules that call into
  this wrapper, not by duplicating `google-genai` calls.