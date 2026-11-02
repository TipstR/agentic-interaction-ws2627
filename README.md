# agentic-interaction-ws2627

Agentic Interaction, WS 2026/27, Ulm University.

**Exercise 1 – First Tool Call:** a small agent that answers questions about the
[mock calendar](https://github.com/jhbelz/agentic-interaction-data) by letting the model call
one tool (`get_calendar_day`). Flow: model → tool → model.

## Setup

Requires Python 3.11 or newer.

```bash
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` in the repository root (never commit it):

```dotenv
OPENAI_BASE_URL=https://api.groq.com/openai/v1
MODEL=openai/gpt-oss-20b
OPENAI_API_KEY=<your Groq key>
DATA_BASE_URL=https://jhbelz.github.io/agentic-interaction-data/v1
```

Environment variables that are already set take precedence over `.env`. Any
OpenAI-compatible endpoint works (the `openai` library is used, not a vendor SDK).

## Run

From the repository root:

```bash
python -m agent "Was steht am 29.10.2026 im Kalender?"
python -m agent "Habe ich morgen Termine?"
```

The answer is printed to standard output; the exit code is `0` on success, `1` on error.
Relative dates ("morgen", "Freitag") are resolved against the mock "now" from
`{DATA_BASE_URL}/context.json`.

## Log

Each run writes its own JSONL file to `logs/` (git-ignored), one line per step:

| Field | Content |
|---|---|
| `ts` | ISO 8601 time stamp |
| `run_id` | one ID per run |
| `event` | `user_task`, `tool_call`, `tool_result`, `final`, `error` |
| `tool`, `args` | tool name and arguments |
| `ok` | whether the step succeeded |
| `model` | model name as sent to the endpoint |
| `duration_ms` | duration of the step |

Additional fields: `task`, `result`, `answer`, `error`.

## Structure

| File | Purpose |
|---|---|
| `agent/__main__.py` | CLI entry point (`python -m agent "…"`) |
| `agent/config.py` | reads `.env` / environment |
| `agent/tools.py` | tool description for the model and the HTTP fetch of `calendar/{YYYY-MM-DD}.json` (404 → "no data" result) |
| `agent/agent.py` | the loop: model → tool → model |
| `agent/runlog.py` | JSONL run log |
