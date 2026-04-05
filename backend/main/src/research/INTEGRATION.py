"""
Integration snippet — add to your existing main FastAPI app file.

Example:
    from main.src.app import app   # your existing FastAPI instance
    from research.router import router as research_router
    app.include_router(research_router)

That's it. The router registers:
    POST   /research/start
    POST   /research/{research_id}/stop
    WS     /research/ws/{research_id}

─── Environment variables to add to your .env ──────────────────────────────────

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_EMBED_MODEL=embeddinggemma:latest

GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile

MCP_SERVER_URL=http://FRIEND_IP:8002

CHROMA_PATH=/data/chroma

REDIS_URL=redis://localhost:6379

─── Full WS message protocol (frontend reference) ──────────────────────────────

OUTGOING (frontend → backend):

  Start answering a clarification question:
  {"type": "user.answer", "answer": "My answer text here"}

  Approve the generated plan:
  {"type": "user.approval", "action": "approve"}

  Request plan refactor with feedback:
  {"type": "user.approval", "action": "refactor", "feedback": "Add a step for X"}

  Stop the research:
  {"type": "stop.request"}

INCOMING (backend → frontend) — all share base fields:
  {"event": "<type>", "research_id": "...", "ts": "ISO8601", ...payload}

  Key events to handle in the UI:

  input.validated        → show cleaned title + description
  input.qa_question      → show question bubble, open input
  input.plan_ready       → render plan checklist (plan[] array)
  input.approved         → mark plan as locked, show "Research starting"

  plan.step_started      → mark step N as "running" in checklist
  plan.step_completed    → mark step N as "done", show summary
  plan.step_failed       → mark step N as "error"
  plan.all_done          → show "Gathering complete"

  tool.called            → show tool activity in thinking panel
  tool.result            → show tool result summary
  think.chunk            → stream into "Agent thinking" section
  react.reason/act/observe → animate ReAct steps

  tokens.update          → update live token counter widget:
                           delta, grand_total, by_model{ollama,groq}, by_step{step_N}

  artifact.chunk         → stream into artifact preview panel
  artifact.done          → mark artifact complete

  stop.requested         → show "Stopping..." banner
  stop.flushing          → show "Saving partial data..."
  stop.saved             → show "Stopped — partial data saved"

  system.progress        → update progress bar (percent 0–100)
  system.error           → show error modal (recoverable bool)
  system.reconnected     → restore UI state (last_step, token_totals)

─── Reconnect flow ──────────────────────────────────────────────────────────────

1. Frontend detects WS disconnect.
2. Frontend reconnects to same WS URL: /research/ws/{research_id}
3. Backend sends system.reconnected with current token totals + last step.
4. Research pipeline was never interrupted — it continued in the background.
5. Frontend resumes receiving events from the current pipeline position.

─── Token counter widget data model ────────────────────────────────────────────

Every tokens.update event carries:
{
  "delta":       142,          // tokens used in this LLM call
  "grand_total": 3847,         // total tokens across entire research
  "by_model": {
    "ollama":    2910,          // tokens used by local Ollama model
    "groq":      937            // tokens used by Groq API
  },
  "by_step": {
    "step_0":    610,
    "step_1":    980,
    "step_2":    2257
  },
  "source":      "ollama/gemma4:e2b",
  "step_index":  2
}

Accumulate by_step to show per-step token bars. Use grand_total for the
main counter. Show by_model as a donut or two progress bars.
"""
