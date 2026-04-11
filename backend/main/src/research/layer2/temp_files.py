"""Temporary markdown file helpers for research orchestration.

Creates per-research temp directories and markdown artifacts used as
intermediate context for synthesis and final artifact generation.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from main.src.research.config import settings


_BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _base_temp_dir() -> Path:
    configured = (settings.TEMP_RESEARCH_BASE_DIR or ".temp").strip()
    base = Path(configured)
    if not base.is_absolute():
        base = _BACKEND_ROOT / base
    return base


def _safe_research_id(research_id: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", research_id.strip())
    return cleaned or "unknown_research"


def ensure_temp_research_dir(research_id: str, existing: str = "") -> str:
    """Return a temp directory path, creating one if needed.

    Directory pattern: .temp/research_{research_id}_{timestamp_ms}
    """
    if existing:
        existing_path = Path(existing)
        if not existing_path.is_absolute():
            existing_path = _BACKEND_ROOT / existing_path
        existing_path.mkdir(parents=True, exist_ok=True)
        return str(existing_path)

    timestamp_ms = int(datetime.utcnow().timestamp() * 1000)
    folder = f"research_{_safe_research_id(research_id)}_{timestamp_ms}"
    temp_dir = _base_temp_dir() / folder
    temp_dir.mkdir(parents=True, exist_ok=True)
    return str(temp_dir)


def step_findings_path(temp_dir: str, step_index: int) -> str:
    path = Path(temp_dir)
    path.mkdir(parents=True, exist_ok=True)
    return str(path / f"step_{step_index + 1}_findings.md")


def append_step_findings(
    temp_dir: str,
    step_index: int,
    sources: list[dict[str, Any]],
    extended_mode: bool = False,
) -> str:
    """
    ## Description

    Append normalized step sources to step_N_findings.md.
    In normal mode, truncates content to 1600 chars.
    In extended mode, writes full content.

    ## Parameters

    - `temp_dir` (`str`)
      - Description: Path to the temp research directory.
      - Constraints: Must be a valid directory path.

    - `step_index` (`int`)
      - Description: Current plan step index (0-based).
      - Constraints: Must be >= 0.

    - `sources` (`list[dict[str, Any]]`)
      - Description: Normalised source dicts from tool parsing.
      - Constraints: Each dict should have title/url/content/tool keys.

    - `extended_mode` (`bool`)
      - Description: When True, writes full source content without truncation.
      - Constraints: Must be a boolean.

    ## Returns

    `str` — Path to the written findings file.
    """
    file_path = Path(step_findings_path(temp_dir, step_index))

    rows: list[str] = []
    rows.append(f"## Step {step_index + 1} findings")
    rows.append(f"Captured at: {datetime.utcnow().isoformat()}Z")
    rows.append("")

    written = 0
    for source in sources:
        title = str(source.get("title", "")).strip()
        url = str(source.get("url", "")).strip()
        content = str(source.get("content", "")).strip()
        tool = str(source.get("tool", "")).strip()

        # Skip summary-only pseudo-sources.
        if not url and not content:
            continue

        written += 1
        rows.append(f"### Source {written}")
        rows.append(f"- Tool: {tool or 'unknown'}")
        rows.append(f"- Title: {title or 'Untitled'}")
        rows.append(f"- URL: {url or 'N/A'}")
        if content:
            snippet = content if extended_mode else content[:1600]
            rows.append("")
            rows.append(snippet)
        rows.append("")

    if written == 0:
        rows.append("No concrete sources captured for this step.")
        rows.append("")

    prefix = "" if not file_path.exists() else "\n"
    with file_path.open("a", encoding="utf-8") as fh:
        fh.write(prefix + "\n".join(rows))

    return str(file_path)


def init_synthesis_file(temp_dir: str, total_sources: int) -> str:
    path = Path(temp_dir)
    path.mkdir(parents=True, exist_ok=True)
    file_path = path / "synthesis.md"
    header = [
        "# Synthesis Context",
        f"Initialized: {datetime.utcnow().isoformat()}Z",
        f"Total sources to analyze: {total_sources}",
        "",
    ]
    file_path.write_text("\n".join(header), encoding="utf-8")
    return str(file_path)


def append_synthesis_entry(
    temp_dir: str,
    source: dict[str, Any],
    analyzed_count: int,
    total_sources: int,
    extended_mode: bool = False,
) -> str:
    """
    ## Description

    Append a single source entry to the synthesis.md file.
    In normal mode, truncates body to 450 chars.
    In extended mode, writes full body.

    ## Parameters

    - `temp_dir` (`str`)
      - Description: Path to the temp research directory.
      - Constraints: Must be a valid directory path.

    - `source` (`dict[str, Any]`)
      - Description: A single normalised source dict.
      - Constraints: Should have title/url/tool/description/content keys.

    - `analyzed_count` (`int`)
      - Description: 1-based index of the current source being analyzed.
      - Constraints: Must be >= 1.

    - `total_sources` (`int`)
      - Description: Total number of sources to analyze.
      - Constraints: Must be >= 1.

    - `extended_mode` (`bool`)
      - Description: When True, writes full body content without truncation.
      - Constraints: Must be a boolean.

    ## Returns

    `str` — Path to the synthesis file.
    """
    file_path = Path(temp_dir) / "synthesis.md"
    file_path.parent.mkdir(parents=True, exist_ok=True)

    title = str(source.get("title", "")).strip() or "Untitled source"
    url = str(source.get("url", "")).strip() or "N/A"
    tool = str(source.get("tool", "")).strip() or "unknown"
    desc = str(source.get("description", "")).strip()
    content = str(source.get("content", "")).strip()
    body = desc or content
    if extended_mode:
        snippet = body if body else "No textual summary available."
    else:
        snippet = body[:450] if body else "No textual summary available."

    lines = [
        f"## [{analyzed_count}/{total_sources}] {title}",
        f"- Tool: {tool}",
        f"- URL: {url}",
        "",
        snippet,
        "",
    ]

    prefix = "" if not file_path.exists() else "\n"
    with file_path.open("a", encoding="utf-8") as fh:
        fh.write(prefix + "\n".join(lines))

    return str(file_path)


def read_synthesis_md(temp_dir: str) -> str:
    file_path = Path(temp_dir) / "synthesis.md"
    if not file_path.exists():
        return ""
    return file_path.read_text(encoding="utf-8")


def write_citations_md(temp_dir: str, citations: list[dict[str, Any]]) -> str:
    path = Path(temp_dir)
    path.mkdir(parents=True, exist_ok=True)
    file_path = path / "citation.md"

    lines = [
        "# Cited Sources",
        f"Generated: {datetime.utcnow().isoformat()}Z",
        "",
    ]

    if not citations:
        lines.append("No citations were collected.")
    else:
        for c in citations:
            idx = c.get("index", "?")
            title = str(c.get("title", "")).strip() or "Untitled"
            url = str(c.get("url", "")).strip() or "N/A"
            lines.append(f"[{idx}] {title}")
            lines.append(url)
            lines.append("")

    content = "\n".join(lines)
    file_path.write_text(content, encoding="utf-8")

    # Backward-compatible duplicate name used in earlier flows.
    legacy_path = path / "cited_sources.md"
    legacy_path.write_text(content, encoding="utf-8")
    return str(file_path)


def read_citations_md(temp_dir: str) -> str:
    canonical = Path(temp_dir) / "citation.md"
    if canonical.exists():
        return canonical.read_text(encoding="utf-8")

    legacy = Path(temp_dir) / "cited_sources.md"
    if legacy.exists():
        return legacy.read_text(encoding="utf-8")

    return ""
