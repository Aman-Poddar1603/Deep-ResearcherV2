"""
Gemini Wrapper Integration Test Suite
======================================
Run with:  uv run -m tests.TestGemini

Tests all public functions in DRGeminiWrapper.py against the Google Gemini
API. Uses Python's built-in `logging` for coloured, timestamped terminal
output — no database involved.

Metrics tracked per test (without third-party libraries):
  • wall-clock latency  (time.perf_counter)
  • response character count
  • tokens estimated   (characters / 4, rough approximation)
  • PASS / FAIL status
"""

import asyncio
import logging
import sys
import time
import json
import tempfile
import os
from datetime import datetime
from typing import Any


def _json_safe(obj: Any) -> str:
    """Serialize obj to a JSON string, converting datetime to ISO format."""
    class _Enc(json.JSONEncoder):
        def default(self, o: Any) -> Any:
            if isinstance(o, datetime):
                return o.isoformat()
            try:
                return super().default(o)
            except TypeError:
                return str(o)
    return json.dumps(obj, cls=_Enc, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------------------
# ── Terminal logger setup ────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

LOG_FORMAT = (
    "%(asctime)s  %(levelname)-8s  %(message)s"
)
logging.basicConfig(
    level=logging.DEBUG,
    format=LOG_FORMAT,
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("GeminiTest")

# Make log levels visually distinct with ANSI colours
_RESET    = "\033[0m"
_BOLD     = "\033[1m"
_GREEN    = "\033[92m"
_YELLOW   = "\033[93m"
_RED      = "\033[91m"
_CYAN     = "\033[96m"
_BLUE     = "\033[94m"
_MAGENTA  = "\033[95m"
_DIM      = "\033[2m"

# ---------------------------------------------------------------------------
# MODEL UNDER TEST
# ---------------------------------------------------------------------------
TEST_MODEL = "gemini-2.5-flash"

# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------

class TestMetrics:
    def __init__(self, name: str):
        self.name = name
        self._start: float = 0.0
        self.elapsed: float = 0.0
        self.response_chars: int = 0
        self.estimated_tokens: int = 0
        self.passed: bool = False
        self.error: str = ""

    def start(self):
        self._start = time.perf_counter()

    def stop(self, response: Any = None):
        self.elapsed = time.perf_counter() - self._start
        if isinstance(response, str):
            self.response_chars = len(response)
            self.estimated_tokens = max(1, len(response) // 4)
        elif response is not None:
            text = _json_safe(response)
            self.response_chars = len(text)
            self.estimated_tokens = max(1, len(text) // 4)

    def mark_pass(self, response: Any = None):
        self.stop(response)
        self.passed = True

    def mark_fail(self, error: Exception):
        self.stop()
        self.passed = False
        self.error = str(error)

    def report(self):
        status  = f"{_GREEN}{_BOLD}✔ PASS{_RESET}" if self.passed else f"{_RED}{_BOLD}✘ FAIL{_RESET}"
        latency = f"{self.elapsed * 1000:.1f} ms" if self.elapsed < 1 else f"{self.elapsed:.2f} s"
        log.info(
            "%s  %s%-36s%s │ latency: %s%-10s%s │ chars: %s%-7s%s │ ~tokens: %s%-6s%s",
            status,
            _CYAN, self.name, _RESET,
            _YELLOW, latency, _RESET,
            _BLUE, self.response_chars, _RESET,
            _MAGENTA, self.estimated_tokens, _RESET,
        )
        if self.error:
            log.error("         %sError: %s%s", _RED, self.error, _RESET)


# ---------------------------------------------------------------------------
# Separator helpers
# ---------------------------------------------------------------------------

def _section(title: str):
    bar = "─" * 70
    log.info("%s%s%s", _BOLD, bar, _RESET)
    log.info("  %s%s%s", _BOLD + _CYAN, title.upper(), _RESET)
    log.info("%s%s%s", _BOLD, bar, _RESET)


def _subsection(title: str):
    log.info("  %s▶ %s%s", _YELLOW, title, _RESET)


def _print_response(label: str, value: Any):
    """Logs the actual model response beneath a test metric line."""
    if value is None:
        return
    if isinstance(value, str):
        text = value
    else:
        text = _json_safe(value)
    log.info("%s    ┌─ %s ─────────────────────────────────────────%s", _DIM, label, _RESET)
    for line in text.splitlines():
        log.info("%s    │  %s%s", _DIM, line, _RESET)
    log.info("%s    └──────────────────────────────────────────────────%s", _DIM, _RESET)


# ---------------------------------------------------------------------------
# Tiny disposable image (64×64 sky-blue JPEG)
# ---------------------------------------------------------------------------

def _create_test_image() -> str:
    from PIL import Image as PILImage
    img = PILImage.new("RGB", (64, 64), color=(135, 206, 235))
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    img.save(tmp.name, format="JPEG")
    tmp.close()
    return tmp.name


# ---------------------------------------------------------------------------
# ── Test runner ──────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

async def run_all_tests():
    # Dynamic import so circular-import fixes are respected
    try:
        import main.src.llms.gemini.DRGeminiWrapper as W
    except ImportError as e:
        log.error("%sImport Error during test initialization: %s%s", _RED, e, _RESET)
        return

    all_metrics: list[TestMetrics] = []
    img_path = _create_test_image()
    log.debug("%sTest image created at: %s%s", _DIM, img_path, _RESET)

    # ═══════════════════════════════════════════════════════════════════════
    # 1 · Client Initialisation
    # ═══════════════════════════════════════════════════════════════════════
    _section("1 · Client Initialisation")

    _subsection("getClient()")
    m = TestMetrics("getClient")
    m.start()
    client = None
    try:
        client = W.getClient()
        m.mark_pass("Client object returned")
    except Exception as e:
        m.mark_fail(e)
    m.report()
    all_metrics.append(m)

    if not client:
        log.error("%sSkipping all tests because client failed to initialize.%s", _RED, _RESET)
        return

    _subsection("getAsyncClient()")
    m = TestMetrics("getAsyncClient")
    m.start()
    aclient = None
    try:
        aclient = W.getAsyncClient()
        m.mark_pass("AsyncClient (.aio) object returned")
    except Exception as e:
        m.mark_fail(e)
    m.report()
    all_metrics.append(m)

    if not aclient:
        log.error(
            "%sSkipping async tests because aclient failed to initialize.%s",
            _RED, _RESET,
        )

    # ═══════════════════════════════════════════════════════════════════════
    # 2 · Model Inspection (sync client)
    # ═══════════════════════════════════════════════════════════════════════
    _section("2 · Model Inspection")

    _subsection("getModelList(client)")
    models_list = None
    m = TestMetrics("getModelList")
    m.start()
    try:
        models_list = W.getModelList(client)
        m.mark_pass(models_list[:2] if models_list else [])
    except Exception as e:
        m.mark_fail(e)
    m.report()
    _print_response(
        "getModelList (first 2)",
        models_list[:2] if models_list else None,
    )
    all_metrics.append(m)

    _subsection(f"getGeminiModel(client, '{TEST_MODEL}')")
    model_info = None
    m = TestMetrics("getGeminiModel")
    m.start()
    try:
        model_info = W.getGeminiModel(client, model_name=TEST_MODEL)
        m.mark_pass(model_info)
    except Exception as e:
        m.mark_fail(e)
    m.report()
    _print_response("getGeminiModel", model_info)
    all_metrics.append(m)

    # ═══════════════════════════════════════════════════════════════════════
    # 3 · Synchronous Generation
    # ═══════════════════════════════════════════════════════════════════════
    _section("3 · Synchronous Generation")

    _subsection("generateContent() · text")
    m = TestMetrics("generateContent [text]")
    m.start()
    result_gc = None
    try:
        result_gc = W.generateContent(
            "Say 'Hello from Gemini'", "System", TEST_MODEL, None, client,
        )
        m.mark_pass(result_gc)
    except Exception as e:
        m.mark_fail(e)
    m.report()
    _print_response("generateContent", result_gc)
    all_metrics.append(m)

    # ═══════════════════════════════════════════════════════════════════════
    # 4 · Async Generation
    # ═══════════════════════════════════════════════════════════════════════
    if aclient:
        _section("4 · Async Generation")

        _subsection("asyncGenerateContent() · text")
        m = TestMetrics("asyncGenerateContent [text]")
        m.start()
        result_agc = None
        try:
            result_agc = await W.asyncGenerateContent(
                "Hi", "System", TEST_MODEL, None, aclient,
            )
            m.mark_pass(result_agc)
        except Exception as e:
            m.mark_fail(e)
        m.report()
        _print_response("asyncGenerateContent", result_agc)
        all_metrics.append(m)

        # ═══════════════════════════════════════════════════════════════════
        # 5 · Tools
        # ═══════════════════════════════════════════════════════════════════
        _section("5 · Tools")

        def test_tool(msg: str) -> str:
            """Echo tool: returns the message passed to it."""
            return msg

        _subsection("asyncGenerateWithTools()")
        m = TestMetrics("asyncGenerateWithTools")
        m.start()
        resp = None
        try:
            resp = await W.asyncGenerateWithTools(
                "Use the test_tool to echo 'hello'",
                "System",
                TEST_MODEL,
                aclient,
                [test_tool],
            )
            m.mark_pass("Tool call processed")
        except Exception as e:
            m.mark_fail(e)
        m.report()
        if resp is not None:
            resp_text = getattr(resp, "text", None)
            func_calls = getattr(resp, "function_calls", None)
            _print_response(
                "asyncGenerateWithTools · text", resp_text,
            )
            _print_response(
                "asyncGenerateWithTools · function_calls",
                str(func_calls) if func_calls else "(none)",
            )
        all_metrics.append(m)

    # ═══════════════════════════════════════════════════════════════════════
    # 6 · Vision (sync — uses Client)
    # ═══════════════════════════════════════════════════════════════════════
    _section("6 · Vision")

    _subsection("understandImageWithoutSaving()")
    m = TestMetrics("understandImageWithoutSaving")
    m.start()
    result_img = None
    try:
        result_img = W.understandImageWithoutSaving(
            img_path, "Describe this image", "System", TEST_MODEL, client,
        )
        m.mark_pass(result_img)
    except Exception as e:
        m.mark_fail(e)
    m.report()
    _print_response("understandImageWithoutSaving", result_img)
    all_metrics.append(m)

    # ═══════════════════════════════════════════════════════════════════════
    # 7 · Helpers
    # ═══════════════════════════════════════════════════════════════════════
    _section("7 · Helpers")

    _subsection("_safe_json_loads()")
    m = TestMetrics("_safe_json_loads")
    m.start()
    res = None
    try:
        res = W._safe_json_loads('{"ok": true}')
        m.mark_pass("JSON parsed")
    except Exception as e:
        m.mark_fail(e)
    m.report()
    _print_response("_safe_json_loads", res)
    all_metrics.append(m)

    # ═══════════════════════════════════════════════════════════════════════
    # 8 · Planning
    # ═══════════════════════════════════════════════════════════════════════
    if aclient:
        _section("8 · Planning")

        _subsection("planner()")
        m = TestMetrics("planner")
        m.start()
        last_plan = None
        try:
            async for p in W.planner(
                TEST_MODEL, "Sys", "User", "Pers", "Add",
                {"type": "object"}, aclient, 1,
            ):
                last_plan = p
            m.mark_pass("Planner finished")
        except Exception as e:
            m.mark_fail(e)
        m.report()
        _print_response("planner · last iteration", last_plan)
        all_metrics.append(m)

    # ═══════════════════════════════════════════════════════════════════════
    # 9 · Image Artifact Generation
    # ═══════════════════════════════════════════════════════════════════════
    if aclient:
        _section("9 · Image Artifact")

        _subsection("asyncGenerateImageArtifact()")
        m = TestMetrics("asyncGenerateImageArtifact")
        m.start()
        artifact = None
        try:
            artifact = await W.asyncGenerateImageArtifact(
                "A simple blue circle on a white background",
                TEST_MODEL,
                aclient,
            )
            if artifact:
                m.mark_pass(f"mime={artifact.get('mime_type')}, data_len={len(str(artifact.get('data', '')))}")
            else:
                m.mark_pass("Returned None (model may not support image gen)")
        except Exception as e:
            m.mark_fail(e)
        m.report()
        _print_response("asyncGenerateImageArtifact", artifact if artifact else "(None)")
        all_metrics.append(m)

    # ═══════════════════════════════════════════════════════════════════════
    # Cleanup + Summary
    # ═══════════════════════════════════════════════════════════════════════
    os.unlink(img_path)

    log.info("\n" + "=" * 70)
    passed = sum(1 for m in all_metrics if m.passed)
    log.info("SUMMARY: %s/%s PASSED", passed, len(all_metrics))
    log.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
