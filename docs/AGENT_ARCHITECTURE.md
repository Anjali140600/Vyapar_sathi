# Vyapar Sathi Agent Architecture

## Overview

Vyapar Sathi now uses a single tool-using financial assistant agent instead of fixed classifier-led routing. The previous approach relied on `if/else` orchestration after classification, which made mixed questions brittle and limited the system to one hard-coded path at a time.

Vyapar Sathi uses a single tool-using financial assistant agent. The agent receives the user query and recent conversation context, then dynamically selects from validated tools for transaction analysis, GST knowledge retrieval, deterministic financial calculations, and bill summarization. It can call multiple tools sequentially for mixed queries, observe their outputs, and synthesize one answer. Database access remains restricted to authenticated, read-only service functions, and a deterministic fallback planner handles invalid local-model output.

This is a single agent, not a multi-agent system. Tool selection is LLM-first, execution is validated, a deterministic fallback exists, and there is no autonomous background execution.

## Why A Single Agent

The chat flow already had one authenticated request context, shared backend services, and a small set of safe capabilities. A single bounded agent loop fits that architecture well because it:

- preserves the existing FastAPI and frontend contract
- supports sequential tool use for mixed questions
- keeps DB access and bill context under trusted server control
- avoids introducing a heavy agent framework for a local Ollama model

## Architecture Diagram

```text
Text / Voice / Image
        |
        v
Trusted preprocessing
- Voice -> STTService
- Image -> OCRService -> trusted bill_data
        |
        v
ChatOrchestrator compatibility facade
        |
        v
VyaparSathiAgent
        |
        +--> query_transactions
        +--> search_gst_knowledge
        +--> calculate_financial_metric
        +--> summarize_bill
        |
        v
Observe tool result
        |
        v
Decide again or finalize
```

## Agent Loop

1. Receive the user query and bounded recent conversation history.
2. Ask the local LLM for one strict JSON action.
3. Validate the action with Pydantic.
4. Execute exactly one approved tool through the registry.
5. Record a sanitized observation.
6. Repeat until a final answer or max-step limit is reached.
7. Synthesize the final answer from successful observations.

If the LLM returns invalid JSON, the system makes one short repair attempt. If that still fails, a deterministic fallback planner takes over.

## Tools

- `query_transactions`: read-only authenticated transaction questions via `DataService.answer_sql_query(...)`
- `search_gst_knowledge`: GST retrieval through `RAGService.query(...)` and `RAGService.build_concise_answer(...)`
- `calculate_financial_metric`: deterministic GST, profit, loss, and margin calculations
- `summarize_bill`: summary over trusted OCR bill data already extracted by the server

## Trusted Context And User Isolation

The agent receives an internal trusted context object with:

- SQLAlchemy session
- authenticated `user_id`
- small recent conversation history window
- optional trusted `bill_data`

The LLM never receives direct access to:

- the database session
- another user's ID
- file paths for arbitrary reading
- credentials or environment secrets

`query_transactions` always injects `context.user_id` server-side, so the model cannot override user isolation.

## LLM Decision JSON Examples

```json
{
  "action": "call_tool",
  "tool_name": "query_transactions",
  "tool_input": {
    "query": "What were my total expenses this month?"
  }
}
```

```json
{
  "action": "final_answer",
  "final_answer": "Your total expenses this month are Rs. 12,500.00."
}
```

## Fallback Planner Behavior

Fallback is used only when LLM decision generation is disabled or invalid. It combines `ClassifierService` with safe keyword checks and follows this order:

1. financial calculation
2. transaction query
3. GST query
4. mixed transaction plus GST sequence
5. bill summary when trusted bill data exists
6. direct general response

## Safety Controls

- bounded loop with `AGENT_MAX_STEPS`
- strict JSON action validation
- one repair attempt per invalid decision
- duplicate tool call blocking
- unknown tool rejection
- clamped RAG result count
- deterministic calculator with no `eval` or dynamic code execution
- trusted bill summarization only from server-produced OCR data
- sanitized trace metadata only
- no raw prompts, stack traces, full DB rows, or full retrieved documents stored in chat metadata

Retrieved GST text and tool outputs are treated as untrusted data, not instructions.

## Conversation History Handling

`chat_router.py` loads a small recent message window for the authenticated conversation, keeps it chronological, and passes only compact `role/content` pairs into the agent. Empty entries and oversized content are trimmed before prompt construction.

## Environment Variables

- `ENABLE_AGENT=true`
- `AGENT_LLM_MODEL=tinyllama`
- `AGENT_MAX_STEPS=4`
- `AGENT_HISTORY_LIMIT=8`
- `AGENT_DEBUG=false`
- `AGENT_DECISION_MAX_CHARS=4000`
- `AGENT_OBSERVATION_MAX_CHARS=3000`

If `AGENT_LLM_MODEL` is absent, the agent reuses `PRIMARY_LLM_MODEL`.

If `ENABLE_AGENT=false`, the deterministic fallback planner still handles supported requests without LLM decisions.

## Local Run

1. Configure `.env`.
2. Start MySQL and any local services you normally use for development.
3. Run the FastAPI app as before.

## Tests

```bash
python -m compileall app llm
python -m pip install -r requirements-dev.txt
pytest -q
```

The unit tests use mocks and fakes, so they do not require MySQL, Ollama, Chroma, Tesseract, Whisper, or internet access.

## Example Queries

- `What are my total expenses this month?`
- `What is input tax credit?`
- `What were my purchases this month and what GST applies to them?`
- `Calculate total price including 18% GST on Rs. 1000.`
- `Summarize this bill.`
- `Hello`

## Known Limitation

TinyLlama may produce invalid structured output, so the implementation uses one repair attempt and then deterministic fallback behavior.
