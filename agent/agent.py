"""The agent loop: model -> tool -> model."""

import json
import time
from datetime import date, datetime

import httpx
from openai import OpenAI

from .config import Config
from .runlog import RunLog
from .tools import TOOLS, get_calendar_day

MAX_ROUNDS = 5  # safety limit; a normal run needs two model calls

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def reference_date(cfg: Config) -> date:
    """'Today' in the mock world (context.json -> now); falls back to the real date."""
    try:
        response = httpx.get(f"{cfg.data_base_url}/context.json", timeout=10)
        response.raise_for_status()
        return datetime.fromisoformat(response.json()["now"]).date()
    except Exception:
        return date.today()


def system_prompt(today: date) -> str:
    return (
        "You are a calendar assistant. "
        f"Today is {WEEKDAYS[today.weekday()]}, {today.isoformat()}. "
        "Resolve relative dates (today, tomorrow, Friday, ...) against this date. "
        "Always look up appointments with the get_calendar_day tool; never invent them. "
        "Answer briefly, in the language of the question, listing time, title and location. "
        "If a day has no appointments or no data, say so."
    )


def run_tool(name: str, args: dict, cfg: Config) -> dict:
    if name == "get_calendar_day":
        return get_calendar_day(cfg.data_base_url, args.get("date"))
    return {"error": f"Unknown tool {name!r}."}


def run_agent(task: str, cfg: Config, log: RunLog) -> str:
    client = OpenAI(base_url=cfg.base_url, api_key=cfg.api_key)
    log.write("user_task", task=task)

    messages = [
        {"role": "system", "content": system_prompt(reference_date(cfg))},
        {"role": "user", "content": task},
    ]

    for round_no in range(MAX_ROUNDS):
        last_round = round_no == MAX_ROUNDS - 1
        start = time.perf_counter()
        response = client.chat.completions.create(
            model=cfg.model,
            messages=messages,
            tools=TOOLS,
            # First call must use the tool; afterwards the model decides.
            # In the last round no tools are allowed so it has to answer.
            tool_choice="required" if round_no == 0 else ("none" if last_round else "auto"),
        )
        model_ms = (time.perf_counter() - start) * 1000
        message = response.choices[0].message

        if not message.tool_calls:
            answer = (message.content or "").strip()
            log.write("final", ok=bool(answer), duration_ms=model_ms, answer=answer)
            return answer

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
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            log.write("tool_call", tool=name, args=args, duration_ms=model_ms)

            start = time.perf_counter()
            result = run_tool(name, args, cfg)
            tool_ms = (time.perf_counter() - start) * 1000
            log.write("tool_result", tool=name, args=args, ok="error" not in result,
                      duration_ms=tool_ms, result=result)

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

    raise RuntimeError("No final answer after the maximum number of rounds.")
