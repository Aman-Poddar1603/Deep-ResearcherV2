"""
agent_service.py — ReAct text-based agent with live MCP-backed tool calling.

## Description

Provides a streaming chat agent that uses a **text-based ReAct loop** to call
MCP tools reliably across ALL Ollama model types, including those that do not
support native structured function calling (tool_calls JSON).

### Why text-based ReAct?

When `bind_tools()` is used with Ollama and the underlying model does not have
native function-calling training (e.g. gemma3, phi3, older llama variants), the
model responds in *plain text* saying it will search, but never emits structured
``tool_calls``.  Text-based ReAct solves this by teaching the model a simple,
parseable output format::

    ACTION: youtube_search
    ACTION_INPUT: {"query": "bali trip"}

Any model capable of following instructions can produce this format reliably.

### Flow

1. Build a tools description block from live MCP tools.
2. Inject it into a system prompt that teaches the ACTION/ACTION_INPUT format.
3. Call `llm.ainvoke()` (non-streaming) to get the model's response.
4. Parse the response for ACTION/ACTION_INPUT directives (text-based) OR
   fall back to native ``tool_calls`` if the model supports them.
5. If a tool call is detected:
   - Run the tool as an ``asyncio.Task`` with 10-minute timeout.
   - Emit periodic ``__THINKING__`` heartbeat tokens every 5 s to keep the
     WebSocket alive during slow external HTTP calls.
   - Feed the result back as ``TOOL RESULT: ...`` in the next message.
   - Loop up to ``_MAX_TOOL_ITERATIONS`` times.
6. When no tool call is found, stream the final text answer token-by-token.

Special ``__THINKING__:<msg>`` sentinel tokens are yielded throughout so
``websocket_handler.py`` can route them to ``{"type": "thinking"}`` frames.

Falls back to a plain LLM call when MCP tools are unavailable.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any, AsyncIterator

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_ollama import ChatOllama

from main.src.research.config import settings
from main.src.research.layer2.tools import get_mcp_tools
from main.src.utils.core.task_schedular import scheduler
from main.src.utils.DRLogger import quickLog


# ── constants ─────────────────────────────────────────────────────────────────

OLLAMA_HOST = settings.OLLAMA_BASE_URL
CHAT_MODEL = settings.OLLAMA_MODEL

_MAX_TOOL_ITERATIONS: int = 5
"""
Maximum number of tool-call/result cycles before forcing a final answer.
Prevents infinite loops when a model keeps requesting tools.
"""

_MAX_TOOL_RESULT_CHARS: int = 6000
"""
Maximum characters kept from a single tool result before trimming.
Web / YouTube / image search return large JSON payloads; without this cap
the combined message list exceeds the model context window.
"""

_TOOL_HEARTBEAT_INTERVAL: float = 5.0
"""
Seconds between ``__THINKING__`` heartbeat sentinels while a slow tool runs.
Keeps the WebSocket alive during external HTTP calls.
"""

_TOOL_MAX_WAIT: float = 600.0
"""
Maximum seconds to wait for a single tool call (10 minutes).
After this the tool task is cancelled and an error result is used.
"""

_THINKING_PREFIX: str = "__THINKING__:"
"""
Sentinel prefix yielded by the agent stream to signal a thinking/status
update. ``websocket_handler.py`` intercepts these and emits a
``{"type": "thinking", "content": "..."}`` WebSocket frame instead of
accumulating the text into the response body.
"""

# ReAct output markers — the model is explicitly told to use these.
_ACTION_MARKER = "ACTION:"
_INPUT_MARKER = "ACTION_INPUT:"

# System prompt injected when tools are available.
# The exact tool list below matches the live MCP server.
_AGENT_SYSTEM_TEMPLATE = """\
You are a helpful AI research assistant with access to live tools.
You MUST use these tools whenever the user asks for searches, videos, images,
or any live/external information. NEVER say you cannot search or access external
data — use the appropriate tool instead.

== AVAILABLE TOOLS ==

1. youtube_search(query: str)
   Search YouTube and return video titles, URLs, channels, descriptions.
   USE for: any request mentioning video, watch, youtube, vlog, tutorial, clip.
   Example:
   ACTION: youtube_search
   ACTION_INPUT: {{"query": "bali travel vlog 2024"}}

2. image_search_tool(queries: list[tuple[str, int]])
   Search for images online. Each tuple is (search_phrase, num_images).
   USE for: any request mentioning image, photo, picture, pic, wallpaper.
   Example:
   ACTION: image_search_tool
   ACTION_INPUT: {{"queries": [["cow images", 10]]}}

3. web_search(query: str)
   Search the web and scrape relevant pages.
   USE for: general questions, news, latest info, facts, anything needing live data.
   Example:
   ACTION: web_search
   ACTION_INPUT: {{"query": "latest AI news 2024"}}

4. read_webpages(urls: list[str])
   Scrape and read content from specific URLs.
   USE when the user provides a URL they want you to read.
   Example:
   ACTION: read_webpages
   ACTION_INPUT: {{"urls": ["https://example.com/article"]}}

5. scrape_single_url(url: str)
   Scrape a single specific URL.
   Example:
   ACTION: scrape_single_url
   ACTION_INPUT: {{"url": "https://example.com/page"}}

6. search_urls_tool(query: str)
   Find URLs related to a query (without scraping their content).
   Example:
   ACTION: search_urls_tool
   ACTION_INPUT: {{"query": "best Python tutorials"}}

7. understand_images_tool(paths: list[str])
   Analyze images using AI to generate titles and descriptions.
   Accepts image URLs or local file paths.
   Example:
   ACTION: understand_images_tool
   ACTION_INPUT: {{"paths": ["https://example.com/image.jpg"]}}

8. process_docs(paths: list[str])
   Process and summarize documents (PDF, DOCX, etc.).
   Example:
   ACTION: process_docs
   ACTION_INPUT: {{"paths": ["https://example.com/doc.pdf"]}}

== HOW TO CALL A TOOL ==
When you need a tool, output EXACTLY these two lines (nothing else before the result):

ACTION: <tool_name>
ACTION_INPUT: <json_object>

Rules:
- Call the tool IMMEDIATELY when the request needs external data — NEVER say
  "I will search" or ask for permission. Just output ACTION/ACTION_INPUT.
- After seeing TOOL RESULT, write your final answer in natural language.
- If no tool is needed, answer directly without any ACTION line.

== OUTPUT FORMAT ==
- Mermaid diagrams: wrap in ```mermaid ... ``` blocks.
- Math equations: use double $$ (single $ not supported).

== RENDERING IMAGES ==
When the context contains image search results formatted as ![alt](url) tags:
- Copy those exact markdown image tags into your response — do NOT rewrite them
  as plain URLs or bullet lists.
- Place multiple images on the same line separated by a space so they render
  in a row (e.g.: ![cat](url1) ![cat](url2) ![cat](url3)).
- After the image row, add a brief description or context about the images.

== RENDERING YOUTUBE RESULTS ==
When the context contains YouTube search results:
- Present them as a numbered list with the video title in bold.
- Include the raw YouTube URL (do NOT use markdown link formatting for the URL), as the frontend will automatically parse it into an iframe.
- Include the channel name, duration, and a one-line description under each.

{context_block}\
"""

# Fallback prompt when no tools are available.
_NO_TOOLS_SYSTEM_PROMPT = (
    "You are a helpful research assistant. Answer clearly and concisely.\n\n"
    "Format instructions:\n"
    "- Mermaid diagrams: wrap in ```mermaid ... ``` blocks.\n"
    "- Math: use double $$ delimiters (single $ not supported).\n"
)


# ── helpers ───────────────────────────────────────────────────────────────────


async def _log(msg: str, level: str = "info", urgency: str = "none") -> None:
    """
    ## Description

    Schedule a background log entry via the task scheduler.

    ## Parameters

    - `msg` (`str`)
      - Description: Log message text.
      - Constraints: Non-empty string.

    - `level` (`str`)
      - Description: Log severity level.
      - Constraints: One of ``"info"``, ``"warning"``, ``"error"``.

    - `urgency` (`str`)
      - Description: Urgency tag for alerting.
      - Constraints: One of ``"none"``, ``"moderate"``, ``"critical"``.

    ## Returns

    `None`
    """
    await scheduler.schedule(
        quickLog, params={"message": msg, "level": level, "urgency": urgency}
    )


def _thinking(message: str) -> str:
    """
    ## Description

    Wrap a status message in the thinking sentinel format so the
    WebSocket handler can forward it as a ``{"type": "thinking"}`` frame.

    ## Parameters

    - `message` (`str`)
      - Description: Human-readable status update.
      - Constraints: Non-empty string.
      - Example: ``"Calling Youtube Search..."``

    ## Returns

    `str` — prefixed sentinel string, e.g. ``"__THINKING__:Calling Youtube Search..."``
    """
    return f"{_THINKING_PREFIX}{message}"


def _normalize_tool_name(tool_name: str) -> str:
    """
    ## Description

    Strip namespace prefixes from an MCP tool name for registry lookup.

    ## Parameters

    - `tool_name` (`str`)
      - Description: Raw tool name as emitted by the model or MCP server.
      - Constraints: Non-empty string.
      - Example: ``"mcp::youtube_search"``

    ## Returns

    `str` — Normalised lowercase tool name, e.g. ``"youtube_search"``.
    """
    name = (tool_name or "").strip().lower()
    if not name:
        return ""
    if "::" in name:
        name = name.split("::")[-1]
    if "/" in name:
        name = name.split("/")[-1]
    if "." in name:
        name = name.split(".")[-1]
    for prefix in ("research_tools_", "mcp_", "tool_"):
        if name.startswith(prefix):
            name = name[len(prefix):]
    return name


def _find_tool(tools: list[Any], name: str) -> Any | None:
    """
    ## Description

    Look up a `BaseTool` by name using normalised comparison.

    ## Parameters

    - `tools` (`list[Any]`)
      - Description: List of `BaseTool` instances from `get_mcp_tools()`.
      - Constraints: May be empty.

    - `name` (`str`)
      - Description: Tool name as emitted by the model.
      - Constraints: Non-empty string.

    ## Returns

    `Any | None` — Matching `BaseTool`, or `None` if not found.
    """
    target = _normalize_tool_name(name)
    for tool in tools:
        if _normalize_tool_name(getattr(tool, "name", "")) == target:
            return tool
    return None


def _build_tools_block(tools: list[Any]) -> str:
    """
    ## Description

    Build a human-readable tools description block injected into the
    agent system prompt.  Each tool gets one line: name + truncated
    description + required input fields.

    ## Parameters

    - `tools` (`list[Any]`)
      - Description: List of `BaseTool` instances.
      - Constraints: Non-empty.

    ## Returns

    `str` — Multi-line tools listing for injection into the system prompt.
    """
    lines: list[str] = []
    for tool in tools:
        name = str(getattr(tool, "name", "")).strip()
        desc = " ".join(str(getattr(tool, "description", "")).split())
        args_schema = getattr(tool, "args_schema", None)
        fields = (
            list(getattr(args_schema, "model_fields", {}).keys())
            if args_schema
            else []
        )
        field_str = f" (inputs: {', '.join(fields)})" if fields else ""
        short_desc = desc[:120] + "..." if len(desc) > 120 else desc
        lines.append(f"- {name}: {short_desc}{field_str}")
    return "\n".join(lines)


def _parse_text_tool_call(text: str) -> tuple[str | None, dict[str, Any]]:
    """
    ## Description

    Parse an ``ACTION: / ACTION_INPUT:`` directive from a model response.

    Supports:
    - The canonical two-line format taught in the system prompt.
    - Loose whitespace and capitalisation variants.
    - JSON wrapped inside markdown code fences.

    ## Parameters

    - `text` (`str`)
      - Description: Raw model response text to scan.
      - Constraints: May be empty or contain only plain prose.

    ## Returns

    `tuple[str | None, dict[str, Any]]`

    ```json
    ["youtube_search", {"query": "bali trip"}]
    ```

    Returns ``(None, {})`` when no valid directive is found.

    ## Debug Notes

    - If the model outputs ``ACTION: tool`` but malformed JSON for
      ``ACTION_INPUT``, the function attempts a ``"query"`` key fallback
      using the raw string as the value.
    """
    # Case-insensitive search for ACTION: followed by ACTION_INPUT: on the
    # next line(s), capturing the tool name and the JSON block.
    pattern = re.compile(
        r"ACTION\s*:\s*(\w+)\s*\n\s*ACTION_INPUT\s*:\s*(\{.*?\})",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return None, {}

    raw_name = match.group(1).strip()
    raw_args = match.group(2).strip()

    # Strip optional markdown fence around the JSON
    raw_args = re.sub(r"^```(?:json)?\s*", "", raw_args)
    raw_args = re.sub(r"\s*```$", "", raw_args)

    try:
        args: dict[str, Any] = json.loads(raw_args)
    except (json.JSONDecodeError, ValueError):
        # Treat the whole string as a query value as a last-resort fallback
        args = {"query": raw_args}

    return raw_name, args


def _extract_native_tool_calls(ai_message: AIMessage) -> list[dict[str, Any]]:
    """
    ## Description

    Extract tool call descriptors from native ``AIMessage.tool_calls``
    (populated by ``bind_tools()`` on Ollama models that support structured
    function calling).

    ## Parameters

    - `ai_message` (`AIMessage`)
      - Description: LLM response message to inspect.
      - Constraints: Must be an ``AIMessage`` instance.

    ## Returns

    `list[dict[str, Any]]`

    Each element:

    ```json
    {
        "id": "call_abc123",
        "name": "youtube_search",
        "args": {"query": "LangChain tutorials"}
    }
    ```

    Returns an empty list when the model did not emit structured calls.
    """
    native: list[Any] = getattr(ai_message, "tool_calls", None) or []
    result: list[dict[str, Any]] = []
    for tc in native:
        if isinstance(tc, dict):
            result.append(
                {
                    "id": tc.get("id") or tc.get("name") or "unknown",
                    "name": tc.get("name", ""),
                    "args": tc.get("args") or {},
                }
            )

    if result:
        return result

    # Legacy additional_kwargs["tool_calls"] (OpenAI-compat format)
    legacy = (getattr(ai_message, "additional_kwargs", None) or {}).get(
        "tool_calls", []
    ) or []
    for tc in legacy:
        if not isinstance(tc, dict):
            continue
        func = tc.get("function") or {}
        raw_args = func.get("arguments") or "{}"
        try:
            args: dict[str, Any] = (
                json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            )
        except (json.JSONDecodeError, ValueError):
            args = {}
        result.append(
            {
                "id": tc.get("id") or func.get("name") or "unknown",
                "name": func.get("name", ""),
                "args": args,
            }
        )
    return result


async def _run_tool_with_heartbeat(
    tool: Any,
    tool_args: dict[str, Any],
    display_name: str,
) -> AsyncIterator[Any]:
    """
    ## Description

    Execute an MCP tool as a background ``asyncio.Task``, yielding
    ``__THINKING__`` heartbeat sentinels every ``_TOOL_HEARTBEAT_INTERVAL``
    seconds so the WebSocket connection stays alive during slow external
    HTTP calls (web search, YouTube, image search).

    The task is hard-cancelled after ``_TOOL_MAX_WAIT`` seconds (10 minutes).

    ## Parameters

    - `tool` (`BaseTool`)
      - Description: LangChain `BaseTool` wrapper for the MCP tool.
      - Constraints: Must expose an ``ainvoke()`` coroutine.

    - `tool_args` (`dict[str, Any]`)
      - Description: Arguments to pass to the tool.
      - Constraints: Must match the tool's ``args_schema``.

    - `display_name` (`str`)
      - Description: Human-readable tool name for heartbeat messages.
      - Constraints: Non-empty string.

    ## Returns

    `AsyncIterator[Any]` — Yields either:

    - ``__THINKING__:<status>`` sentinel strings (heartbeats).
    - A single final value: the raw tool result on success, or an
      ``Exception`` instance on failure / timeout.

    ## Side Effects

    - Creates and cancels ``asyncio.Task`` objects.
    - Logs timeout/failure events via the background scheduler.

    ## Debug Notes

    - If the tool never completes, it is cancelled after ``_TOOL_MAX_WAIT``
      seconds and the caller receives a timeout error result string.
    """
    tool_task: asyncio.Task[Any] = asyncio.create_task(tool.ainvoke(tool_args))
    elapsed: float = 0.0

    while not tool_task.done():
        try:
            await asyncio.wait_for(
                asyncio.shield(tool_task),
                timeout=_TOOL_HEARTBEAT_INTERVAL,
            )
        except asyncio.TimeoutError:
            elapsed += _TOOL_HEARTBEAT_INTERVAL
            if elapsed >= _TOOL_MAX_WAIT:
                tool_task.cancel()
                yield _thinking(f"{display_name} timed out after {int(elapsed)}s.")
                yield TimeoutError(
                    f"Tool '{display_name}' exceeded the {int(_TOOL_MAX_WAIT)}s limit."
                )
                return
            if not tool_task.done():
                yield _thinking(
                    f"{display_name} still running ({int(elapsed)}s)..."
                )
        except Exception:
            break

    try:
        yield tool_task.result()
    except Exception as exc:
        yield exc


# ── streaming agent runner ────────────────────────────────────────────────────


async def stream_agent_response(
    query: str,
    context: str,
) -> AsyncIterator[str]:
    """
    ## Description

    Run a ReAct-style text-based agent that uses live MCP tools and yields
    text tokens plus ``__THINKING__`` sentinel updates.

    Unlike native function-calling (``bind_tools``), this approach works with
    **any Ollama model** because the agent communicates tool intent as plain
    text using ``ACTION:`` / ``ACTION_INPUT:`` directives that are parsed
    server-side.

    ### Loop (up to ``_MAX_TOOL_ITERATIONS``):

    1. Call ``llm.ainvoke(messages)``.
    2. Check for native ``tool_calls`` (capable models) OR parse
       ``ACTION:`` / ``ACTION_INPUT:`` directives (any model).
    3. If a tool call is detected: run via MCP with heartbeats → inject
       ``TOOL RESULT:`` into messages → repeat.
    4. If no tool call: stream the final answer and return.

    ## Parameters

    - `query` (`str`)
      - Description: The user's current question.
      - Constraints: Non-empty string.
      - Example: ``"Find YouTube videos about bali trip"``

    - `context` (`str`)
      - Description: Pre-built context block produced by
        ``rag_service.build_context()`` (history, RAG chunks, etc.).
      - Constraints: May be empty.

    ## Returns

    `AsyncIterator[str]`

    Yields either:

    - Plain text tokens to accumulate into the response.
    - ``__THINKING__:<status>`` sentinels intercepted by ``websocket_handler``.

    ## Side Effects

    - Connects to MCP server via ``get_mcp_tools()``.
    - Invokes MCP tools via ``BaseTool.ainvoke()``.
    - Background-logs events via the task scheduler.

    ## Debug Notes

    - If the model outputs ``ACTION:`` correctly but the tool is not found,
      check that the tool name matches exactly what was listed in the tools block.
    - Raise the log level to ``DEBUG`` in ``tools.py`` to trace MCP session
      open/close events.
    - Tool execution time is bounded by ``_TOOL_MAX_WAIT`` (10 minutes).

    ## Customization

    - Adjust ``_MAX_TOOL_ITERATIONS`` for deeper multi-step reasoning.
    - Adjust ``_MAX_TOOL_RESULT_CHARS`` to control context usage per tool call.
    - Adjust ``_TOOL_MAX_WAIT`` to change the per-tool timeout.
    """
    llm = ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_HOST,
        temperature=0.2,
        keep_alive=True,
        reasoning=False,
    )

    # ── 1. Load MCP tools ─────────────────────────────────────────────────
    tools: list[Any] = []
    try:
        yield _thinking("Loading MCP tools...")
        tools = await get_mcp_tools()
        await _log(
            f"[agent] Loaded {len(tools)} MCP tool(s): "
            + ", ".join(getattr(t, "name", "?") for t in tools),
            level="info",
        )
    except Exception as exc:
        await _log(
            f"[agent] Failed to load MCP tools: {exc}",
            level="warning",
            urgency="moderate",
        )

    # ── 2. Build system prompt ────────────────────────────────────────────
    # The template has the complete tool list hardcoded for precision.
    # Only inject the optional context block (history, RAG chunks, etc.).
    context_block = f"=== CONTEXT ===\n{context}" if context.strip() else ""

    if tools:
        system_content = _AGENT_SYSTEM_TEMPLATE.format(context_block=context_block)
    else:
        system_content = _NO_TOOLS_SYSTEM_PROMPT
        if context.strip():
            system_content += f"\n\n=== CONTEXT ===\n{context}"


    messages: list[BaseMessage] = [
        SystemMessage(content=system_content),
        HumanMessage(content=query),
    ]

    # ── 3. ReAct loop ─────────────────────────────────────────────────────
    for iteration in range(_MAX_TOOL_ITERATIONS):
        yield _thinking(
            "Thinking..."
            if iteration == 0
            else f"Thinking (step {iteration + 1})..."
        )

        try:
            response: AIMessage = await llm.ainvoke(messages)  # type: ignore[assignment]
        except Exception as exc:
            await _log(
                f"[agent] LLM invoke error (iteration {iteration}): {exc}",
                level="error",
                urgency="critical",
            )
            yield "I hit an error while generating a response."
            return

        response_text = (
            response.content if isinstance(response.content, str) else ""
        )

        # ── 4a. Detect tool call — native tool_calls first ─────────────
        tool_name: str = ""
        tool_args: dict[str, Any] = {}
        native_calls = _extract_native_tool_calls(response)
        if native_calls:
            tool_name = native_calls[0]["name"]
            tool_args = native_calls[0].get("args") or {}
            await _log(
                f"[agent] Native tool_call detected: {tool_name} args={tool_args}",
                level="info",
            )
        else:
            # ── 4b. Detect tool call — text-based ReAct parsing ────────
            tool_name, tool_args = _parse_text_tool_call(response_text)
            if tool_name:
                await _log(
                    f"[agent] Text-based ACTION detected: {tool_name} args={tool_args}",
                    level="info",
                )

        if not tool_name:
            # ── 5. No tool call → final answer ────────────────────────
            if not response_text.strip():
                yield "I couldn't generate a response."
                return

            # Stream the already-collected text in chunks (no second LLM call)
            chunk_size = 8
            for start in range(0, len(response_text), chunk_size):
                yield response_text[start: start + chunk_size]
                await asyncio.sleep(0)
            return

        # ── 6. Execute the tool ───────────────────────────────────────
        found_tool = _find_tool(tools, tool_name) if tools else None
        display_name = tool_name.replace("_", " ").title()

        if found_tool is None:
            await _log(
                f"[agent] Tool not found: {tool_name}",
                level="warning",
                urgency="none",
            )
            result_text = f"Tool '{tool_name}' is not available."
        else:
            yield _thinking(f"Calling {display_name}...")
            result_text = ""

            async for item in _run_tool_with_heartbeat(
                found_tool, tool_args, display_name
            ):
                if isinstance(item, str) and item.startswith(_THINKING_PREFIX):
                    yield item  # heartbeat sentinel → pass through
                    continue
                if isinstance(item, Exception):
                    await _log(
                        f"[agent] Tool {tool_name} failed: {item}",
                        level="warning",
                        urgency="moderate",
                    )
                    result_text = f"Tool '{tool_name}' returned an error: {item}"
                else:
                    # Normalise raw tool result to a string
                    raw = item
                    if isinstance(raw, str):
                        result_text = raw
                    else:
                        try:
                            result_text = json.dumps(raw, ensure_ascii=True)
                        except (TypeError, ValueError):
                            result_text = str(raw)

                    # Truncate to avoid context overflow
                    if len(result_text) > _MAX_TOOL_RESULT_CHARS:
                        result_text = (
                            result_text[:_MAX_TOOL_RESULT_CHARS]
                            + f"\n\n[Result truncated to {_MAX_TOOL_RESULT_CHARS} chars]"
                        )

                    await _log(
                        f"[agent] Tool {tool_name} completed ({len(result_text)} chars)",
                        level="info",
                    )

        # ── 7. Inject tool result and continue loop ───────────────────
        # Append assistant message (with ACTION directive) then result
        messages.append(AIMessage(content=response_text))
        messages.append(
            HumanMessage(
                content=(
                    f"TOOL RESULT for {tool_name}:\n{result_text}\n\n"
                    "Now give your final answer based on the above result."
                )
            )
        )
        yield _thinking("Processing tool results...")
        # tool_name / tool_args are re-initialised at the top of the next iteration.

    # ── 8. Iteration cap → force a final answer ───────────────────────────
    await _log(
        f"[agent] Reached max tool iterations ({_MAX_TOOL_ITERATIONS}), "
        "requesting final answer.",
        level="warning",
        urgency="none",
    )
    messages.append(
        HumanMessage(
            content="Please summarise the tool results above and give a final answer."
        )
    )
    try:
        async for chunk in llm.astream(messages):
            token = chunk.content if isinstance(chunk.content, str) else ""
            if token:
                yield token
    except Exception as exc:
        await _log(
            f"[agent] Final answer streaming error: {exc}",
            level="error",
            urgency="critical",
        )
        yield "I hit an error while generating a final response."


async def _plain_llm_stream(
    query: str,
    context: str,
) -> AsyncIterator[str]:
    """
    ## Description

    Fallback plain LLM stream without tool binding.

    Used when MCP tools are unavailable and the caller explicitly
    needs a non-tool path.

    ## Parameters

    - `query` (`str`)
      - Description: User query.
      - Constraints: Non-empty string.

    - `context` (`str`)
      - Description: Context block built by ``rag_service.build_context()``.
      - Constraints: May be empty.

    ## Returns

    `AsyncIterator[str]` — Plain text token stream.

    ## Side Effects

    - Calls Ollama LLM via ``ChatOllama.astream()``.
    - Logs errors via background scheduler.
    """
    llm = ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_HOST,
        temperature=0.2,
        keep_alive=True,
        reasoning=False,
    )
    system_content = _NO_TOOLS_SYSTEM_PROMPT
    if context.strip():
        system_content += f"\n\n=== CONTEXT ===\n{context}"

    messages: list[BaseMessage] = [
        SystemMessage(content=system_content),
        HumanMessage(content=query),
    ]
    try:
        async for chunk in llm.astream(messages):
            token = chunk.content if isinstance(chunk.content, str) else ""
            if token:
                yield token
    except Exception as exc:
        await _log(
            f"[agent] Plain LLM error: {exc}", level="error", urgency="critical"
        )
        yield "I hit an error while generating a response."
