# agentic-interaction-ws2627

Agentic Interaction, WS 2026/27, Ulm University.

**Exercise 3 – The Agent Loop:** an agent that answers questions about the
[mock calendar](https://github.com/jhbelz/agentic-interaction-data) with one tool
(`get_calendar_day`). It calls the model in a loop, runs the requested tool calls and stops
by itself as soon as the model answers without asking for another tool.

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
Relative dates ("morgen", "Freitag") are resolved against the real current date
(`date.today()`).

## How a run ends

- **Answer:** the model replies without a tool call. Log ends with `final`, exit code `0`.
- **Step limit:** after 10 model calls (`MAX_ROUNDS` in `agent/agent.py`) without an answer
  the run stops. Log ends with `error` (`StepLimitError`), exit code `1`.
- **Fatal error:** wrong API key, unknown model, missing configuration. Log ends with
  `error`, exit code `1`.

A single step that goes wrong does not end the run:

- A failed tool call (invalid date, unknown tool, unparsable arguments, data server
  unreachable) is returned to the model as `{"error": ...}` and logged as `tool_result`
  with `ok: false`.
- A failed model call (rate limit, malformed tool call, outage) or an empty reply is logged
  as `error` with `fatal: false`; it uses up one round and the loop continues.

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

Additional fields: `task`, `result`, `answer`, `error`, `round` (number of the model call),
`fatal` (`false` on an `error` that did not end the run).

## Manual tests

A fixed list of typical questions (`manual_tests/questions.py`) is asked one after the
other. The answers are not checked automatically; you read the report.

```bash
python -m manual_tests                 # all questions
python -m manual_tests --only 1,5,7    # a subset
```

"Today" is pinned to 2026-10-28 (change it with `--today`) so that relative dates hit the
mock calendar (2026-10-26 to 2026-11-08). Each run writes `test_runs/<timestamp>.md` with,
for every question: what to check, the answer, the tool calls made, rounds used, the path
to its JSONL log and an empty pass/fail field.

## Structure

| File | Purpose |
|---|---|
| `agent/__main__.py` | CLI entry point (`python -m agent "…"`) |
| `agent/config.py` | reads `.env` / environment |
| `agent/tools.py` | tool description for the model and the HTTP fetch of `calendar/{YYYY-MM-DD}.json` (404 → "no data" result) |
| `agent/agent.py` | the agent loop, step limit and per-step error handling |
| `agent/runlog.py` | JSONL run log |
| `manual_tests/` | test questions and the runner that writes the review report |
