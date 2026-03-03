---
name: google-genai-codegen
description: Generate correct, up-to-date Python code using the Google Gen AI (google-genai) SDK for Gemini Developer API and Vertex AI, including content generation, chats, interactions, tools, JSON schemas, and streaming. Use when the user wants code that talks to Gemini models via the google-genai client or mentions google-genai, google.genai, genai.Client, Gemini Developer API, Vertex AI, or deep-research agents.
---

# Google Gen AI SDK Codegen

This skill makes the agent generate **correct, modern Python code** using the `google-genai` SDK, avoiding outdated APIs and guesswork.

Focus on:
- Using `google-genai` patterns exactly as documented.
- Choosing the **right client setup** (Gemini Developer API vs Vertex AI).
- Producing clean, minimal, and copy‑paste‑ready examples.

---

## Quick Start

### Imports

Always start with the canonical imports:

```python
from google import genai
from google.genai import types
```

Only add extra imports (e.g. `time`, `asyncio`, `pydantic`) when they are clearly needed.

### Installation (reference only, usually not in code)

If needed for context, reference installation succinctly:

```bash
pip install google-genai
# or
uv pip install google-genai
```

Do **not** repeat installation commands inside every code snippet unless the user explicitly asks.

---

## Client Creation

### Preferred pattern: use environment variables

Assume the key is provided via environment variables whenever reasonable.

**Gemini Developer API (recommended default):**

Environment variables:

```bash
export GEMINI_API_KEY='your-api-key'
# or
export GOOGLE_API_KEY='your-api-key'
```

Python:

```python
from google import genai

client = genai.Client()
```

Use this pattern unless the user explicitly wants inline `api_key` or Vertex AI.

### Inline API key (only when user asks)

```python
from google import genai

client = genai.Client(api_key="GEMINI_API_KEY")
```

Do **not** invent additional keyword arguments for `Client` beyond what the SDK supports.

### Vertex AI client

Only use this when the user explicitly says they are on Vertex AI / GCP project:

Environment:

```bash
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT='your-project-id'
export GOOGLE_CLOUD_LOCATION='us-central1'
```

Python (env-based):

```python
from google import genai

client = genai.Client()
```

Python (explicit):

```python
from google import genai
from google.genai import types

client = genai.Client(
    vertexai=True,
    project="your-project-id",
    location="us-central1",
    http_options=types.HttpOptions(api_version="v1"),  # use v1 when user wants stable API
)
```

### Context manager pattern (preferred for multiple calls)

When showing multiple calls, prefer a context manager to avoid “client has been closed” issues:

```python
from google.genai import Client

MODEL_ID = "gemini-2.5-flash"

with Client() as client:
    response_1 = client.models.generate_content(
        model=MODEL_ID,
        contents="Hello",
    )
    response_2 = client.models.generate_content(
        model=MODEL_ID,
        contents="Ask a question",
    )

    print(response_1.text)
    print(response_2.text)
```

Use this pattern when:
- There are multiple requests, or
- The user mentions resource cleanup / connection issues.

---

## Basic Text Generation

### Simple text input → text output

Use the canonical `generate_content` call:

```python
from google import genai

client = genai.Client()
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Why is the sky blue?",
)
print(response.text)
```

Guidelines:

- Use realistic, current model IDs like `"gemini-2.5-flash"` unless the user specifies others.
- Use `contents=...` exactly as documented.

---

## Using `types` and Configs

When users need more control (temperature, safety, JSON, images, etc.), use `types.GenerateContentConfig`.

### Using `types.Part` and `GenerateContentConfig`

```python
from google import genai
from google.genai import types

client = genai.Client()

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=types.Part.from_text(text="Why is the sky blue?"),
    config=types.GenerateContentConfig(
        temperature=0.3,
        top_p=0.95,
        top_k=20,
        system_instruction="Answer concisely.",
    ),
)

print(response.text)
```

### Structuring `contents`

Follow the SDK rules and do **not** invent new forms.

Common patterns:

- **String input (auto-wrapped):**

  ```python
  contents="Why is the sky blue?"
  ```

- **List of strings (single user content with multiple parts):**

  ```python
  contents=["Why is the sky blue?", "Why is the cloud white?"]
  ```

- **Explicit `types.Content`:**

  ```python
  from google.genai import types

  contents = types.Content(
      role="user",
      parts=[types.Part.from_text(text="Why is the sky blue?")],
  )
  ```

For mixed multimodal or function calls, use the patterns from the docs (group function call parts into `ModelContent`, non-function parts into `UserContent`) instead of inventing new roles.

---

## JSON Output & Schemas

When the user wants **structured JSON**, prefer `response_mime_type="application/json"` and `response_json_schema`.

### JSON Schema as Python dict

```python
from google import genai

client = genai.Client()

user_profile = {
    "type": "object",
    "title": "User Schema",
    "properties": {
        "username": {
            "type": "string",
            "description": "User's unique name",
        },
        "age": {
            "anyOf": [
                {"type": "integer", "minimum": 0, "maximum": 20},
                {"type": "null"},
            ],
            "title": "Age",
        },
    },
    "required": ["username", "age"],
}

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Give me a random user profile.",
    config={
        "response_mime_type": "application/json",
        "response_json_schema": user_profile,
    },
)

print(response.text)
```

Do **not** ask the model to “output JSON like this example” when using schemas; rely on the schema instead.

### JSON Schema from Pydantic

```python
from pydantic import BaseModel
from google import genai
from google.genai import types

class CountryInfo(BaseModel):
    name: str
    population: int
    capital: str
    continent: str
    gdp: int
    official_language: str
    total_area_sq_mi: int

client = genai.Client()

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Give me information for the United States.",
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=CountryInfo.model_json_schema(),
    ),
)

print(response.text)
```

---

## Streaming

When the user asks for **streaming responses**, use the documented stream APIs rather than manual chunking hacks.

### Sync streaming

```python
from google import genai

client = genai.Client()

for chunk in client.models.generate_content_stream(
    model="gemini-2.5-flash",
    contents="Tell me a story in 300 words.",
):
    if chunk.text:
        print(chunk.text, end="")
```

### Async streaming

```python
from google import genai

aclient = genai.Client().aio

async def main():
    async for chunk in await aclient.models.generate_content_stream(
        model="gemini-2.5-flash",
        contents="Tell me a story in 300 words.",
    ):
        if chunk.text:
            print(chunk.text, end="")

# Run with asyncio.run(main())
```

Match sync vs async to the user’s environment preference.

---

## Chats (Multi-turn)

Use chats when the user wants **conversation state** on the client side.

### Sync chat

```python
from google import genai

client = genai.Client()

chat = client.chats.create(model="gemini-2.5-flash")

response = chat.send_message("Tell me a story.")
print(response.text)

response = chat.send_message("Summarize the story in one sentence.")
print(response.text)
```

### Async chat

```python
from google import genai

aclient = genai.Client().aio

async def main():
    chat = aclient.chats.create(model="gemini-2.5-flash")
    response = await chat.send_message("Tell me a story.")
    print(response.text)

    response = await chat.send_message("Summarize the story in one sentence.")
    print(response.text)
```

Use chats instead of manually threading `contents` across turns when the user wants a conversational interface.

---

## Interactions & Deep Research

When the user mentions **Interactions API** or **deep research agents**, use the `client.interactions` interface.

### Basic interaction

```python
from google import genai

client = genai.Client()

interaction = client.interactions.create(
    model="gemini-2.5-flash",
    input="Tell me a short joke about programming.",
)

print(interaction.outputs[-1].text)
```

### Deep Research agent (background)

```python
import time
from google import genai

client = genai.Client()

initial_interaction = client.interactions.create(
    input="Research the history of the Google TPUs with a focus on 2025 and 2026.",
    agent="deep-research-pro-preview-12-2025",
    background=True,
)

while True:
    interaction = client.interactions.get(id=initial_interaction.id)
    if interaction.status == "completed":
        print(interaction.outputs[-1].text)
        break
    if interaction.status in ["failed", "cancelled"]:
        raise RuntimeError(f"Deep research failed: {interaction.status}")
    time.sleep(10)
```

Keep the agent name exactly as documented when referenced; do not rename it.

---

## Tools & Function Calling

When the user wants **tool calling**, follow SDK patterns.

### Automatic Python function tool

```python
from google import genai
from google.genai import types

client = genai.Client()

def get_current_weather(location: str) -> str:
    """Returns the current weather."""
    return "sunny"

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="What is the weather like in Boston?",
    config=types.GenerateContentConfig(
        tools=[get_current_weather],
    ),
)

print(response.text)
```

### Manual function declaration & follow-up

```python
from google import genai
from google.genai import types

client = genai.Client()

function = types.FunctionDeclaration(
    name="get_current_weather",
    description="Get the current weather in a given location",
    parameters_json_schema={
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city and state, e.g. San Francisco, CA",
            },
        },
        "required": ["location"],
    },
)

tool = types.Tool(function_declarations=[function])

def get_current_weather(location: str) -> str:
    return "sunny"

user_prompt_content = types.Content(
    role="user",
    parts=[types.Part.from_text(text="What is the weather like in Boston?")],
)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[user_prompt_content],
    config=types.GenerateContentConfig(tools=[tool]),
)

function_call = response.function_calls[0]
function_call_content = response.candidates[0].content

try:
    function_result = get_current_weather(**function_call.function_call.args)
    function_response = {"result": function_result}
except Exception as e:
    function_response = {"error": str(e)}

function_response_part = types.Part.from_function_response(
    name=function_call.name,
    response=function_response,
)
function_response_content = types.Content(
    role="tool",
    parts=[function_response_part],
)

follow_up = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[user_prompt_content, function_call_content, function_response_content],
    config=types.GenerateContentConfig(tools=[tool]),
)

print(follow_up.text)
```

Do not invent non-documented fields on `FunctionDeclaration`, `Tool`, or `AutomaticFunctionCallingConfig`.

---

## Embeddings, Images, Video (Veo), Files, Caches, Batch, Tunings

When users explicitly ask for these capabilities:

- **Embeddings**: use `client.models.embed_content(...)` with `types.EmbedContentConfig` when extra config is needed.
- **Images (Imagen)**: use `client.models.generate_images`, `upscale_image`, `edit_image` with `types.GenerateImagesConfig` / `EditImageConfig`.
- **Video (Veo)**: use `client.models.generate_videos` and poll operations with `client.operations.get(...)`.
- **Files**: use `client.files.upload`, `get`, `delete` for Gemini Developer API file workflows.
- **Caches**: use `client.caches.create/get` and `GenerateContentConfig(cached_content=...)`.
- **Batch jobs**: use `client.batches.create/list/get/delete`.
- **Tunings**: use `client.tunings.tune/get/list` and tuned model endpoints for inference.

When demonstrating these, keep examples **short** and always follow the patterns shown in the official docs (no custom polling protocols or fake fields).

---

## Error Handling

Use the SDK’s `APIError` instead of generic exception text when talking to the model service.

```python
from google import genai
from google.genai import errors

client = genai.Client()

try:
    client.models.generate_content(
        model="invalid-model-name",
        contents="What is your name?",
    )
except errors.APIError as e:
    print(e.code)
    print(e.message)
```

Do not swallow errors silently in examples; show at least basic handling.

---

## General Codegen Guidelines

- **Do not invent methods or attributes** on `client`, `client.models`, `client.chats`, `client.interactions`, `client.files`, `client.caches`, `client.batches`, or `client.tunings`.
- Prefer **simple, minimal examples** that compile and run as-is.
- Match sync vs async to the user’s requirements; never mix them in a single small example unless explicitly teaching both.
- When the user’s request conflicts with documented behavior, **prioritize the official patterns** from this skill and the SDK docs, and explain the constraint briefly in natural language outside the code.
- For model names, use **current Gemini families** mentioned by the user or in the docs (e.g. `gemini-2.5-flash`, `gemini-2.5-flash-image`, `veo-3.1-generate-preview`) without inventing new suffixes.

