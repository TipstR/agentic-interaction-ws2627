"""The agent loop: model -> tool -> model."""

import json
import time
from datetime import date, timedelta

from openai import APIError, AuthenticationError, NotFoundError, OpenAI, PermissionDeniedError

from .config import Config
from .runlog import RunLog
from .tools import TOOLS, get_calendar_day, get_connections, get_weather

MAX_ROUNDS = 10  # step limit: model calls per run; hitting it is an error

# Model errors that no retry can fix.
FATAL_MODEL_ERRORS = (AuthenticationError, PermissionDeniedError, NotFoundError)


class StepLimitError(RuntimeError):
    """The run used up MAX_ROUNDS model calls without a final answer."""


WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


HOME_CITY = "Ulm"  # the user's home (context.json of the mock data)


def system_prompt(today: date) -> str:
    # Spell out the dates of this week and the next: small models get weekday arithmetic wrong.
    monday = today - timedelta(days=today.weekday())
    days = [monday + timedelta(days=i) for i in range(14)]
    this_week = ", ".join(f"{WEEKDAYS[d.weekday()][:3]} {d.isoformat()}" for d in days[:7])
    next_week = ", ".join(f"{WEEKDAYS[d.weekday()][:3]} {d.isoformat()}" for d in days[7:])
    return (
        "You are a personal assistant for calendar, weather and train travel. "
        f"Today is {WEEKDAYS[today.weekday()]}, {today.isoformat()}. "
        f"This week (Monday to Sunday): {this_week}. Next week: {next_week}. "
        "Resolve relative dates (today, tomorrow, Friday, ...) against these dates. "
        "To find the next appointment after a day, keep checking the following days one by "
        "one until you find one or reach a day with no data. "
        f"The user lives in {HOME_CITY}; if a trip has no starting point, assume {HOME_CITY} "
        "and say so.\n"
        "Tools: get_calendar_day for appointments, get_weather for the forecast of a city, "
        "get_connections for trains between two cities. A question may need several tools; "
        "call all that are needed before answering (e.g. for 'how do I get to X and do I need "
        "an umbrella', look up the connections to X and the weather in X on that day).\n"
        "Only state facts that a tool returned. Never invent appointments, temperatures, "
        "weather, trains or times. If a tool returns no_data, say plainly that there is no "
        "data for that place or day (not that nothing happens), and still answer the parts "
        "you do have data for. No calendar data means no data, not a free day.\n"
        "Answer briefly, always in the language of the user's question, even though the "
        "data is partly German. Appointments: time, title, location. "
        "Trains: departure, arrival, train, changes. Weather: condition, temperature and rain "
        "probability, plus a clear yes/no if the user asks about an umbrella."
    )


# Tool name -> function(data_base_url, args). Missing arguments arrive as None
# and are rejected by the tool itself with an {"error": ...} result.
TOOL_FUNCS = {
    "get_calendar_day": lambda base, a: get_calendar_day(base, a.get("date")),
    "get_weather": lambda base, a: get_weather(base, a.get("city"), a.get("date")),
    "get_connections": lambda base, a: get_connections(
        base, a.get("from_city"), a.get("to_city"), a.get("date")),
}


def run_tool(name: str, args: dict, cfg: Config) -> dict:
    """Run one tool. Never raises: a failure is returned as {"error": ...}
    so the model sees it and the run continues."""
    func = TOOL_FUNCS.get(name)
    if func is None:
        return {"error": f"Unknown tool {name!r}. Available: {', '.join(TOOL_FUNCS)}."}
    try:
        return func(cfg.data_base_url, args)
    except Exception as exc:  # network failure, HTTP 5xx, broken JSON, ...
        return {"error": f"Tool {name} failed: {type(exc).__name__}: {exc}"}


def run_agent(task: str, cfg: Config, log: RunLog, today: date | None = None) -> str:
    """Loop until the model answers without tool calls.

    `today` pins the date relative dates are resolved against (used by the
    manual tests); None means the real current date.

    Every round is one model call. A step that goes wrong (failed model call,
    unparsable arguments, failed tool) is logged and the loop carries on.
    Reaching MAX_ROUNDS without an answer raises StepLimitError, which
    __main__ logs as an error and turns into exit code 1.
    """
    client = OpenAI(base_url=cfg.base_url, api_key=cfg.api_key)
    today = today or date.today()
    log.write("user_task", task=task, today=today.isoformat())

    messages = [
        {"role": "system", "content": system_prompt(today)},
        {"role": "user", "content": task},
    ]

    for round_no in range(1, MAX_ROUNDS + 1):
        start = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=cfg.model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
        except FATAL_MODEL_ERRORS:
            raise  # wrong key / wrong model: retrying cannot help
        except APIError as exc:
            # One failed model call (rate limit, malformed tool call, outage)
            # costs a round but does not end the run.
            model_ms = (time.perf_counter() - start) * 1000
            log.write("error", ok=False, duration_ms=model_ms, round=round_no, fatal=False,
                      error=f"Model call failed, continuing: {type(exc).__name__}: {exc}")
            continue
        model_ms = (time.perf_counter() - start) * 1000
        message = response.choices[0].message

        if not message.tool_calls:
            answer = (message.content or "").strip()
            if answer:
                log.write("final", ok=True, duration_ms=model_ms, round=round_no, answer=answer)
                return answer
            log.write("error", ok=False, duration_ms=model_ms, round=round_no, fatal=False,
                      error="Model returned neither an answer nor a tool call, continuing.")
            messages.append({"role": "user", "content":
                             "Your last reply was empty. Call a tool or give the final answer."})
            continue

        # Echo the assistant turn (with its tool calls) back into the history.
        messages.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.function.name, "arguments": call.function.arguments},
                }
                for call in message.tool_calls
            ],
        })

        for call in message.tool_calls:
            name = call.function.name
            bad_args = None
            try:
                args = json.loads(call.function.arguments or "{}")
                if not isinstance(args, dict):
                    bad_args = "Tool arguments must be a JSON object."
            except json.JSONDecodeError as exc:
                bad_args = f"Tool arguments are not valid JSON: {exc}"
            if bad_args:
                args = {"raw": call.function.arguments}
            log.write("tool_call", tool=name, args=args, duration_ms=model_ms, round=round_no)

            start = time.perf_counter()
            result = {"error": bad_args} if bad_args else run_tool(name, args, cfg)
            tool_ms = (time.perf_counter() - start) * 1000
            log.write("tool_result", tool=name, args=args, ok="error" not in result,
                      duration_ms=tool_ms, round=round_no, result=result)

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

    raise StepLimitError(f"Step limit reached: no final answer after {MAX_ROUNDS} model calls.")
