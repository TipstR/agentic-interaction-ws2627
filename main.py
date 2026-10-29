import json
import os
from datetime import date

import httpx
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq()


def ask(prompt):
    response = client.chat.completions.create(
        model=os.environ.get("MODEL"),
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def get_today_calendar():
    url = f"{os.environ['DATA_BASE_URL']}/calendar/{date.today().isoformat()}.json"
    response = httpx.get(url)
    response.raise_for_status()
    return response.json()


# What the model sees: name, description and parameters (JSON Schema) of each tool
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_today_calendar",
            "description": "Get the user's calendar events for today.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

# What actually runs when the model calls a tool
TOOL_FUNCTIONS = {
    "get_today_calendar": get_today_calendar,
}


def run_agent(prompt):
    messages = [{"role": "user", "content": prompt}]
    while True:
        response = client.chat.completions.create(
            model=os.environ.get("MODEL"),
            messages=messages,
            tools=TOOLS,
        )
        message = response.choices[0].message

        # No tool requested -> the model has its final answer
        if not message.tool_calls:
            return message.content

        messages.append(message)
        for tool_call in message.tool_calls:
            args = json.loads(tool_call.function.arguments or "{}")
            result = TOOL_FUNCTIONS[tool_call.function.name](**args)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })


if __name__ == '__main__':
    print(run_agent("What's on my calendar today?"))
