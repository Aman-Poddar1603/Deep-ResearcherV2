"""
## Description

Module responsible for executing asynchronous database persistence 
tasks dispatched from the core Research Orchestrator. Relies on the 
global DBManager components to securely interface with SQLite engines.

## Side Effects

- Writes payload directly to `researches.db` and `history.db` SQLite stores.
- Mutates database states without returning values to the caller.
"""

import json
import uuid
from typing import List, Dict, Any
from main.src.store.DBManager import researches_db_manager, history_db_manager

async def persist_research_event(job_id: str, event_dict: Dict[str, Any]) -> None:
    """
    ## Description

    Asynchronously stores a research tracking event into the history database. 
    It queries the core `researches` table to inherently map the internal 
    `workspace_id` to maintain strict referential boundaries.

    ## Parameters

    - `job_id` (`str`)
      - Description: Targeted research session UUID.
      - Constraints: Must match a valid `researches.id`.
      - Example: "550e8400-e29b-41d4-a716-446655440000"

    - `event_dict` (`Dict[str, Any]`)
      - Description: Formatted Dictionary containing event metadata.
      - Constraints: Must contain 'stage'.
      
    ## Returns

    `None`

    Structure:

    ```json
    null
    ```

    ## Raises

    - `Exception`
      - Bubble up underlying database execution failures implicitly handled by scheduler.

    ## Side Effects

    - Invokes `DBManager.fetch_one()` to obtain `workspace_id`.
    - Invokes `DBManager.insert()` on `research_history` table.

    ## Debug Notes

    - Expect failures if `job_id` is somehow purged beforehand preventing `workspace_id` lookup.
    """
    workspace_id = None
    res = researches_db_manager.fetch_one("researches", {"id": job_id})
    if res.get("success") and res.get("data"):
        workspace_id = res["data"].get("workspace_id")

    payload = {
        "id": str(uuid.uuid4()),
        "research_id": job_id,
        "workspace_id": workspace_id,
        "activity": event_dict.get("stage", "UNKNOWN"),
        "actions": json.dumps(event_dict),
    }
    history_db_manager.insert("research_history", payload)


async def persist_research_findings(job_id: str, step_findings: List[Dict[str, str]]) -> None:
    """
    ## Description

    Asynchronously interates step summarisation arrays and inserts individual
    scraped results natively into the `research_sources` database mappings.

    ## Parameters

    - `job_id` (`str`)
      - Description: Targeted research session UUID.
      - Constraints: Must match a valid `researches.id`.

    - `step_findings` (`List[Dict[str, str]]`)
      - Description: List of structurally summarized findings from external sources.
      - Constraints: Each dict must contain 'source' and 'summary' keys.
      - Example: 
        ```python
        [{"source": "https://example.com", "summary": "Example output text"}]
        ```

    ## Returns

    `None`

    Structure:

    ```json
    null
    ```

    ## Raises

    - `KeyError` 
      - When iteration objects lack necessary dict key types unhandled.

    ## Side Effects

    - Mutates `research_sources` dynamically extending historical reference arrays.

    ## Debug Notes

    - Assumes the pipeline executes and emits correctly structured `List[Dict]` layouts.
    """
    for finding in step_findings:
        payload = {
            "id": str(uuid.uuid4()),
            "research_id": job_id,
            "source_type": "scraping",
            "source_url": finding.get("source", ""),
            "source_content": finding.get("summary", "")
        }
        researches_db_manager.insert("research_sources", payload)


async def persist_research_artifact(job_id: str, artifact_dict: Dict[str, Any]) -> None:
    """
    ## Description

    Asynchronously stores the final compiled markdown structural artifact
    directly onto the active `researches` core database tracking session payload.

    ## Parameters

    - `job_id` (`str`)
      - Description: Targeted research session UUID.
      - Constraints: Must match a valid `researches.id`.

    - `artifact_dict` (`Dict[str, Any]`)
      - Description: Compounded Markdown artifact payload to JSON serialize cleanly.
      - Constraints: Unrestricted dynamic keys.
      
    ## Returns

    `None`

    Structure:

    ```json
    null
    ```

    ## Raises

    - `Exception`
      - Underlying JSON parsing issues natively if schema is wildly malformed internally.

    ## Side Effects

    - Invokes `DBManager.update()` directly modifying existing global application properties.

    ## Debug Notes

    - Validates target `job_id` execution completion tracking states.
    """
    researches_db_manager.update(
        "researches", 
        {"artifacts": json.dumps(artifact_dict)}, 
        {"id": job_id}
    )
