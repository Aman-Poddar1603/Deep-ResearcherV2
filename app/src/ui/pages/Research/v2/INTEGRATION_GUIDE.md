# Realtime Resumable Research Integration Specification

Version: 2026-04-12
Status: Runtime-conformance spec for this repository

This is a strict implementation specification for integrating the same backend protocol into a different frontend.

Primary goal:

- Prevent implementation drift and hallucinated contracts.

Scope:

- REST + WebSocket contracts
- Resume/replay/cursor protocol
- Event ingestion and reducer semantics
- Persistent session storage contract
- Operational guardrails and conformance checks

Out of scope:

- Visual/UI layout guidance
- Styling/component advice
- Non-runtime README examples

## 1) Source of truth

Bachend raw api agent!

## 2) Normative language

The words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are normative.

## 3) Locked constants and storage keys

The integration MUST use these constants unless runtime code changes:

- DEFAULT_BASE_URL: http://localhost:8000
- DEFAULT_REPLAY_LIMIT: 500
- Resume storage key: research.resume.sessions.v1
- Backend base URL storage key: research.backend.base_url.v1
- WS backoff base: 500 ms
- WS backoff cap: 8000 ms
- Resume replay pagination hard pass cap: 20 loops

## 4) Canonical backend contract

### 4.1 REST endpoints

1. Start research

- Method: POST
- Path: /research/start
- Body: JSON object payload

2. Resume bundle

- Method: GET
- Path: /research/{researchId}/resume
- Query:
  - includeTimeline: true/false
  - fromEventId: cursor
  - timelineLimit: integer

3. Status

- Method: GET
- Path: /research/{researchId}/status

4. Replay

- Method: GET
- Path: /research/{researchId}/events/replay
- Query:
  - fromEventId: cursor
  - limit: integer

5. Stop

- Method: POST
- Path: /research/{researchId}/stop

MUST NOT use these stale paths:

- /research/{id}/start
- /research/ws/research/{id}

### 4.2 WebSocket endpoint

- Path: /research/ws/{researchId}
- Query on connect:
  - last_event_id: cursor (optional if empty)
  - replay_limit: integer (always sent)

### 4.3 Outbound WebSocket messages

Only these outbound message shapes are used by runtime:

1. QA answer
   {
   "type": "user.answer",
   "answer": "string"
   }

2. Plan approval
   {
   "type": "user.approval",
   "action": "approve"
   }

3. Plan refactor request
   {
   "type": "user.approval",
   "action": "refactor",
   "feedback": "string"
   }

4. Stop request
   {
   "type": "stop.request"
   }

No other outbound types are required by this app.

## 5) URL normalization rules (strict)

For each research_id, runtime MUST derive canonical URLs from backendBase:

- status_url: /research/{id}/status
- replay_url: /research/{id}/events/replay
- resume_url: /research/{id}/resume
- websocket_url: /research/ws/{id}

When backend provides URLs:

- Resolve to absolute if possible.
- If invalid/missing, fallback to canonical.

WebSocket protocol normalization:

- http -> ws
- https -> wss
- ws/wss preserved

## 6) Payload and response contracts

### 6.1 Start payload (canonical shape used by app)

{
"prompt": "string",
"sources": [],
"workspace_id": "string",
"system_prompt": "string",
"custom_prompt": "string",
"title": "string",
"description": "string",
"research_template": "string",
"ai_personality": "string",
"username": "string"
}

Behavioral rules:

- Runtime accepts only JSON object payload from editor input.
- Missing keys fallback to default payload values.

### 6.2 Start response parsing

Runtime extraction rules:

- research_id from response.research_id, fallback response.id.
- research_id then validated by robust extractor (reject empty and "[object Object]").
- status is optional string.
- runtime URLs are normalized regardless of backend quality.

### 6.3 Resume bundle expected fields

Core fields consumed:

- research_id
- status
- current_step
- total_steps
- latest_event_id
- token_totals
- pending_input
- context
- plan
- timeline_events[]
- timeline_replay_count
- timeline_next_event_id
- status_url
- replay_url
- resume_url
- websocket_url

Optional snapshot fields consumed when present:

- streaming_snapshot.latest_event_id
- streaming_snapshot.artifact_text
- streaming_snapshot.thinking_by_step
- streaming_snapshot.recent_tool_results

### 6.4 Status response expected fields

- research_id
- status
- current_step
- total_steps
- token_totals
- latest_event_id
- pending_input

### 6.5 Replay response expected fields

- events[]
- replay_count
- next_event_id

## 7) Session status model

Canonical statuses:

- idle
- connecting
- connected
- starting
- waiting_for_answer
- waiting_for_approval
- running
- stopping
- stopped
- completed
- failed
- disconnected
- not_found

Terminal statuses:

- completed
- stopped
- failed
- not_found

Alias normalization mapping:

- layer1_qa -> waiting_for_answer
- qa -> waiting_for_answer
- waiting_for_input -> waiting_for_answer
- plan_approval -> waiting_for_approval
- awaiting_plan_approval -> waiting_for_approval
- approval_required -> waiting_for_approval
- researching -> running
- executing -> running
- done -> completed
- error -> failed
- canceled -> stopped
- cancelled -> stopped
- expired -> not_found

## 8) Cursor protocol (monotonic)

### 8.1 Accepted cursor formats

- Integer-like string: "123"
- Stream-like string: "123-0"
- Numeric value

Invalid/empty cursors MUST be ignored.

### 8.2 Source priority

When ordering cannot be compared, source priority is:

- timeline = 3
- stream = 2
- status = 1

### 8.3 Update rules

1. If new cursor is backward relative to current, reject.
2. If equal, ignore.
3. If non-comparable, accept only if source priority is >= current source priority.
4. On accept, update:

- local cursor ref
- stream manager cursor
- persisted session record

## 9) Event envelope and field extraction

### 9.1 Event name extraction precedence

Runtime resolves event name from first match:

- data.event
- data.event_type
- data.type (must include ".")
- data.eventName
- data.payload.event
- data.payload.event_type
- data.payload.type (must include ".")
- data.payload.eventName

If no event name, drop message.

### 9.2 Timestamp extraction

- Use data.ts
- else data.payload.ts
- else current ISO timestamp

### 9.3 Generic event field extraction

For all event fields, runtime reads:

1. top-level key
2. payload.key

This is mandatory because replay rows may be payload-wrapped.

### 9.4 Cursor extraction candidates

Runtime checks, in order, across top-level, payload, metadata, and meta:

- id
- stream_id / streamId
- event_id / eventId
- latest_event_id / latestEventId
- next_event_id / nextEventId
- timeline_next_event_id / timelineNextEventId

First cursor-like value wins.

## 10) Event dedup algorithm

### 10.1 Tracker capacities

- seenEventIds max: 8000
- seenFingerprints max: 4000
- seenSemanticFingerprints max: 6000

### 10.2 Volatile keys removed for semantic dedup

- event_id, eventId
- latest_event_id, latestEventId
- next_event_id, nextEventId
- timeline_next_event_id, timelineNextEventId
- ts, timestamp

### 10.3 Semantic dedup event set

Explicit semantic dedup list:

- input.qa_question
- input.plan_ready
- input.approved
- plan.step_started
- plan.step_completed
- plan.step_failed
- plan.all_done
- stop.requested
- stop.flushing
- stop.saved

Additionally:

- Any event starting with tool. uses semantic dedup.

### 10.4 Should-apply checks

Drop event if any is true:

1. eventId exists and was seen
2. semanticFingerprint exists and was seen
3. no eventId and raw fingerprint was seen

### 10.5 Tool event ID fallback

If no cursor-like ID, tool events may synthesize eventId as:

- tool:{eventName}:{toolId}

Tool ID candidates:

- tool_id / toolId
- tool_call_id / toolCallId
- call_id / callId
  (top-level or payload)

## 11) Normalized event aliases

Runtime alias normalization in reducer:

- tool.call -> tool.called
- tool.started -> tool.called
- tool.invoke -> tool.called
- tool.invoked -> tool.called
- tool.completed -> tool.result
- tool.done -> tool.result
- tool.success -> tool.result
- tool.failed -> tool.error

Important nuance:

- Semantic dedup normalization in timelineReducer maps:
  - tool.call -> tool.called
  - tool.started -> tool.called
  - tool.completed -> tool.result
  - tool.failed -> tool.error
- It does not normalize tool.invoke, tool.invoked, tool.done, tool.success for semantic fingerprints.
- App-level alias normalization still maps those before switch-case handling.

## 12) Reducer behavior by event

Only listed behavior is guaranteed.

1. system.connected

- status = normalized(status) fallback connected
- clear error

2. system.reconnected

- status = normalized(status) fallback connected
- clear error
- refresh tokens from token_totals when present

3. system.progress

- progress from progress or percent
  - if value in [0,1], convert to percent\*100 and round
  - else round as percent
- progressMsg from message when present

4. system.error

- error text from message or "Backend error"
- if recoverable=false -> status failed

5. input.validated

- cleaned text from prompt or cleaned_prompt
- stores validated input card data

6. input.qa_question

- queues question by question_index (or next index)
- status waiting_for_answer

7. input.plan_ready

- stores plan text via toPlanText
- status waiting_for_approval

8. input.approved

- clears pending input
- status running
- planApproved = confirmed when provided else true

9. plan.step_started

- ensures step exists at step_index
- marks step running

10. react.reason / think.chunk

- appends chunk from first available:
  - chunk
  - reasoning
  - thought
  - text
- uses overlap-safe appendStreamChunk

11. think.done

- marks step thinkingDone=true
- if full_thought present, finalizes text with finalizeText

12. react.act

- appends note from tool_name/name + action + text

13. react.observe

- appends observation note from:
  - observation
  - observation_summary
  - text

14. tool.called

- creates tool row
- dedup by explicit tool ID first
- else dedup by same (tool_name + args signature)

15. tool.result

- matches tool by ID first
- else by signature
- writes result from:
  - result_summary
  - result
  - output

16. tool.error

- matches tool by ID first
- else by signature
- writes error from error or message

17. plan.step_completed

- marks step completed
- summary from summary or result

18. plan.step_failed

- marks step failed
- error from error field or fallback

19. plan.all_done

- progress=100
- status=completed

20. tokens.update

- tokens normalized from token_totals or event object

21. artifact.chunk

- appends chunk from chunk or text

22. artifact.done

- artifact final from artifact or existing text
- artifactDone=true
- status=completed

23. stop.requested

- status=stopping
- stopState=requested

24. stop.flushing

- status=stopping
- stopState=flushing
- progressMsg from message when present

25. stop.saved

- status=stopped
- stopState=saved

## 13) Token normalization contract

Token normalization accepts multiple backend formats.

Input fallback order:

1. input_tokens
2. inputTokens
3. by_direction.input
4. by_direction.in
5. sum(by_step_direction.\*.input)
6. 0

Output fallback order:

1. output_tokens
2. outputTokens
3. by_direction.output
4. by_direction.out
5. sum(by_step_direction.\*.output)
6. 0

Total fallback order:

1. total_tokens
2. totalTokens
3. grand_total
4. total
5. input + output

## 14) Runtime flows (strict)

### 14.1 Start flow (Connect and Start)

Triggered by startResearch:

1. Reset run state to starting.
2. POST /research/start.
3. Normalize runtime URLs.
4. Persist resumable record.
5. Navigate to /session/{id}.
6. Open WebSocket immediately.

### 14.2 New session generation flow (Generate / + New)

Triggered by newSession:

1. Reset run state.
2. POST /research/start.
3. Normalize URLs and persist record.
4. Navigate to /session/{id}.
5. Set status idle.
6. DO NOT auto-open WebSocket.

This difference is intentional and MUST be preserved.

### 14.3 Connect flow

Triggered by connect():

- Calls resumeAndJoin(researchId, includeLiveStream=true).
- There is no separate REST connect endpoint.

### 14.4 Resume and join flow

1. Validate research_id (reject empty or "[object Object]").
2. Disconnect current stream and reset to connecting.
3. Load local session record and canonicalize URLs.
4. Seed cursor from local last_known_event_id when present.
5. Call resume with:

- includeTimeline=true
- fromEventId=localCursor or "0-0"
- timelineLimit=1000

6. Hydrate snapshot state from bundle.
7. Apply bundle.timeline_events through dedup reducer.
8. Advance cursor using timeline_next_event_id else latest_event_id.
9. If timeline appears truncated:

- condition: timeline_replay_count >= 1000 and timeline_next_event_id exists
- call replay(limit=500) repeatedly
- stop when replay_count < 500 or next_event_id missing
- hard cap 20 passes

10. If status non-terminal and includeLiveStream=true, open WS.
11. If terminal or includeLiveStream=false, keep stream disconnected.

### 14.5 Session list refresh flow

Used on home page for existing local sessions:

- Calls resume with:
  - includeTimeline=false
  - fromEventId=record.last_known_event_id or "0-0"
  - timelineLimit=50
- On success, upserts refreshed runtime URLs and latest status snapshot.
- On session-not-found, removes local record and marks as expired in UI list.

### 14.6 Stop flow

1. Send WS message {"type":"stop.request"}.
2. Optimistically set status stopping and stopState requested.
3. POST /research/{id}/stop.
4. Continue processing stop.\* events.

If REST stop fails, error is set but stream/event handling continues.

### 14.7 Disconnect flow

1. manualDisconnect=true
2. Close socket
3. status=idle

### 14.8 Polling flow

Poll interval: 5000 ms.

Poll only when status is one of:

- connecting
- starting
- connected
- running
- waiting_for_answer
- waiting_for_approval
- stopping
- disconnected

Polling updates:

- status
- progress/progressMsg
- token_totals
- pending_input
- latest_event_id cursor
- persisted snapshot

Polling errors:

- session-not-found -> handle as terminal not_found and cleanup
- other errors -> non-fatal (ignored for loop continuity)

## 15) WebSocket lifecycle behavior

Send behavior:

- send() is a no-op when socket state is not OPEN.

onOpen:

- reset reconnectAttempt to 0
- clear reconnect timer
- status becomes connected unless already in live states

onClose:

- if manual close, transition to idle
- if terminal status, do nothing
- else transition to disconnected and queue reconnect

Reconnect gate:

- shouldReconnect = !manualDisconnect && !isTerminalStatus(currentStatus)

Backoff formula:

- delay = round(min(8000, 500 _ 2^attempt) _ (1 + random\*0.2))

## 16) Session-not-found handling

Detection logic:

1. ResumeApiError with status 404
2. ResumeApiError payload.detail contains "session not found" or "stale"
3. Generic Error message contains "session not found" or "stale"

On detection:

- Disconnect stream with manual flag.
- Remove record from storage.
- Clear timeline/dedup/cursor refs.
- status = not_found
- error = "This session is no longer available."
- Treat as terminal read-only.

## 17) Persistent session contract

Storage key:

- research.resume.sessions.v1

Record shape:
{
"research_id": "string",
"status_url": "string",
"replay_url": "string",
"resume_url": "string",
"websocket_url": "string",
"last_known_event_id": "string|number|null",
"last_status": "object|null",
"pending_input": "object|null",
"updated_at": "number"
}

Store requirements:

- Upsert MUST normalize runtime URLs.
- Read MUST migrate legacy entries and rewrite map when changed.
- listSortedRecent MUST return records sorted by updated_at desc.

## 18) Production guardrails (anti-hallucination)

Your production agent MUST:

1. Use only endpoints and fields listed in this spec.
2. Preserve Start vs New flow differences.
3. Preserve cursor monotonic behavior and source-priority fallback.
4. Preserve dedup stages (eventId -> semantic -> fingerprint).
5. Read event fields from root and payload fallback.
6. Keep resume/replay limits exactly unless backend contract is explicitly changed.
7. Keep 5-second polling safety net for active-like statuses.
8. Preserve terminal behavior: no reconnect for completed/stopped/failed/not_found.

Your production agent MUST NOT:

1. Invent /research/{id}/start.
2. Invent /research/ws/research/{id}.
3. Assume a dedicated connect REST endpoint exists.
4. Move cursor backward.
5. Drop resume timeline/replay dedup logic.
6. Assume events always use top-level fields.
7. Auto-mark stopped without stop.saved or terminal status evidence.

## 19) Conformance checklist (must pass)

Use this as a release gate for integration:

1. Start button path opens WS immediately after POST /research/start.
2. New session generation path does not auto-open WS.
3. Resume path calls includeTimeline=true, fromEventId, timelineLimit=1000.
4. Replay catch-up pages from cursor with limit=500 and max 20 passes.
5. WS URL includes replay_limit and optional last_event_id.
6. Event wrapper payload fields are parsed correctly.
7. Duplicate events from resume+replay+stream do not duplicate reducer effects.
8. Cursor never regresses.
9. Poll loop runs every 5s in active-like statuses.
10. Session-not-found cleans storage and sets not_found terminal state.
11. Stop flow sends both WS stop.request and REST stop.
12. Terminal sessions do not reconnect.
