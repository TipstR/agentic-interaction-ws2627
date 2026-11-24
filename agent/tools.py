"""The agent's tools: calendar, weather and train connections from the mock data.

Every tool returns a dict that is sent back to the model. "No data" (HTTP 404,
unknown city) and invalid input are returned as results, not raised, so the
agent keeps running. Network failures and HTTP 5xx do raise; run_tool() in
agent.py turns them into {"error": ...}.
"""

import re
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

GET_WEATHER = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": (
            "Returns the weather forecast for one city on one day: temperature in °C, "
            "condition (in German, e.g. 'Regen' = rain, 'Schauer' = showers), "
            "rain probability (0..1) and wind in km/h. "
            "Call it for any question about weather, temperature, rain, or whether an "
            "umbrella or jacket is needed. For a trip, look up the destination city. "
            "Forecasts exist only for some cities and days; a result with no_data=true "
            "means there is no forecast, so do not guess one."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name, e.g. 'Ulm' or 'München' (Munich).",
                },
                "date": {
                    "type": "string",
                    "description": "The day, ISO format YYYY-MM-DD, e.g. 2026-10-29.",
                },
            },
            "required": ["city", "date"],
            "additionalProperties": False,
        },
    },
}

GET_CONNECTIONS = {
    "type": "function",
    "function": {
        "name": "get_connections",
        "description": (
            "Returns the train connections from one city to another on one day: "
            "departure and arrival time, train, number of changes and price in EUR. "
            "Call it for any question about how to get somewhere, trains, or travel times. "
            "For a round trip, call it once per direction. "
            "Connections exist only for some routes and days; a result with no_data=true "
            "means there is no timetable, so do not guess one."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "from_city": {
                    "type": "string",
                    "description": "Departure city, e.g. 'Ulm'.",
                },
                "to_city": {
                    "type": "string",
                    "description": "Destination city, e.g. 'München' (Munich).",
                },
                "date": {
                    "type": "string",
                    "description": "The travel day, ISO format YYYY-MM-DD, e.g. 2026-10-29.",
                },
            },
            "required": ["from_city", "to_city", "date"],
            "additionalProperties": False,
        },
    },
}

TOOLS = [GET_CALENDAR_DAY, GET_WEATHER, GET_CONNECTIONS]

# Names the model might use for a city -> the slug used in the data paths.
CITY_ALIASES = {"munich": "muenchen", "munchen": "muenchen", "monaco di baviera": "muenchen"}


def city_slug(name) -> str | None:
    """'München' / 'Munich' / 'muenchen' -> 'muenchen'. None if not a plausible name."""
    if not isinstance(name, str):
        return None
    slug = name.strip().lower()
    slug = slug.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    slug = CITY_ALIASES.get(slug, slug)
    # Only letters and dashes, so the name cannot escape the URL path.
    slug = re.sub(r"\s+", "-", slug)
    return slug if re.fullmatch(r"[a-z]+(-[a-z]+)*", slug) else None


def parse_date(date_str) -> date | None:
    try:
        return date.fromisoformat(date_str)
    except (TypeError, ValueError):
        return None


def fetch(url: str) -> dict | None:
    """GET a JSON file. None means HTTP 404, i.e. no data."""
    response = httpx.get(url, timeout=10)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def get_calendar_day(data_base_url: str, date_str: str) -> dict:
    """Fetch {DATA_BASE_URL}/calendar/{YYYY-MM-DD}.json."""
    day = parse_date(date_str)
    if day is None:
        return {"error": f"Invalid date {date_str!r}, expected YYYY-MM-DD."}

    data = fetch(f"{data_base_url}/calendar/{day.isoformat()}.json")
    if data is None:
        return {"date": day.isoformat(), "no_data": True,
                "message": "The calendar has no data for this day (HTTP 404)."}
    return data


def get_weather(data_base_url: str, city: str, date_str: str) -> dict:
    """Fetch {DATA_BASE_URL}/weather/{city}/{YYYY-MM-DD}.json."""
    day = parse_date(date_str)
    if day is None:
        return {"error": f"Invalid date {date_str!r}, expected YYYY-MM-DD."}
    slug = city_slug(city)
    if slug is None:
        return {"error": f"Invalid city name {city!r}."}

    data = fetch(f"{data_base_url}/weather/{slug}/{day.isoformat()}.json")
    if data is None:
        return {"city": city, "date": day.isoformat(), "no_data": True,
                "message": "No weather data for this city and day (HTTP 404). The forecast "
                           "is unknown; do not estimate one."}
    return data


def get_connections(data_base_url: str, from_city: str, to_city: str, date_str: str) -> dict:
    """Fetch {DATA_BASE_URL}/transit/{from}/{to}/{YYYY-MM-DD}.json."""
    day = parse_date(date_str)
    if day is None:
        return {"error": f"Invalid date {date_str!r}, expected YYYY-MM-DD."}
    src, dst = city_slug(from_city), city_slug(to_city)
    if src is None or dst is None:
        bad = from_city if src is None else to_city
        return {"error": f"Invalid city name {bad!r}."}

    data = fetch(f"{data_base_url}/transit/{src}/{dst}/{day.isoformat()}.json")
    if data is None:
        return {"from": from_city, "to": to_city, "date": day.isoformat(), "no_data": True,
                "message": "No timetable data for this route and day (HTTP 404). This does "
                           "not mean no trains run, only that they are unknown; do not make "
                           "up trains or times."}
    return data
