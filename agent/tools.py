"""The single tool: read the appointments of one day from the mock calendar."""

from datetime import date

import httpx

# What the model sees: name, purpose and parameters (JSON Schema).
GET_CALENDAR_DAY = {
    "type": "function",
    "function": {
        "name": "get_calendar_day",
        "description": (
            "Returns all appointments in the user's calendar for exactly one day "
            "(title, start and end time, all-day flag, location). "
            "Call it whenever a question concerns what is scheduled on a date. "
            "For several days, call it once per day."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "The day to look up, ISO format YYYY-MM-DD, e.g. 2026-10-29.",
                },
            },
            "required": ["date"],
            "additionalProperties": False,
        },
    },
}

TOOLS = [GET_CALENDAR_DAY]


def get_calendar_day(data_base_url: str, date_str: str) -> dict:
    """Fetch {DATA_BASE_URL}/calendar/{YYYY-MM-DD}.json.

    Returns a dict that is sent back to the model. A 404 ("no data") or an
    invalid date is returned as a result, not raised, so the agent keeps running.
    """
    try:
        day = date.fromisoformat(date_str)
    except (TypeError, ValueError):
        return {"error": f"Invalid date {date_str!r}, expected YYYY-MM-DD."}

    url = f"{data_base_url}/calendar/{day.isoformat()}.json"
    response = httpx.get(url, timeout=10)
    if response.status_code == 404:
        return {"date": day.isoformat(), "no_data": True,
                "message": "The calendar has no data for this day (HTTP 404)."}
    response.raise_for_status()
    return response.json()
