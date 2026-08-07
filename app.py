"""TripSmith — AI Travel Trip Planner.

Built on Google Gen AI SDK (google-genai), extending Lab GSP1150 (Introduction to Gemini 3).
Lab features used: System Instructions, Function calling, Multimodality,
Multi-turn chat + streaming, thinking_level. Plus Structured Output (JSON schema).
"""

import argparse
import json
import mimetypes
import os
import urllib.request
from enum import Enum

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv()

# Lab GSP1150 uses Gemini 3.1 Pro and Gemini 3.5 Flash.
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

SYSTEM_INSTRUCTION = (
    "You are TripSmith, an experienced local travel guide.\n"
    "- Give practical, realistic trip plans — leave enough time to travel between places.\n"
    "- Match the traveler's budget and interests; don't suggest places that are closed or out of season.\n"
    "- Pick real local spots, not tourist traps.\n"
    "- Keep it short and clear. When asked for JSON, output ONLY valid JSON that matches the schema."
)


# ---- Structured Output schema ----
class TimeOfDay(str, Enum):
    morning = "morning"
    afternoon = "afternoon"
    evening = "evening"


class Activity(BaseModel):
    time_of_day: TimeOfDay
    title: str
    description: str
    approx_cost_usd: float = Field(ge=0)
    duration_hours: float = Field(gt=0)


class DayPlan(BaseModel):
    day: int
    theme: str
    activities: list[Activity]


class TripPlan(BaseModel):
    destination: str
    trip_month: str
    num_days: int
    summary: str
    days: list[DayPlan]
    packing_tips: list[str]
    estimated_total_cost_usd: float


def get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("Missing GEMINI_API_KEY. Copy .env.example to .env and set it.")
    return genai.Client(api_key=api_key)


# ---- Feature: Function calling (lab get_weather pattern) ----
def get_weather(location: str) -> dict:
    """Get the current weather in a specific location.

    Args:
        location: The city and country, e.g. Kyoto, Japan.
    """
    # Placeholder for a real weather API call.
    return {"location": location, "temperature": "18", "unit": "celsius", "sky": "clear"}


def fetch_weather(client: genai.Client, destination: str) -> str:
    resp = client.models.generate_content(
        model=MODEL,
        contents=f"What is the weather like in {destination} right now?",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.2,  # facts, not creativity
            tools=[get_weather],  # SDK auto-calls this Python function
        ),
    )
    return resp.text or ""


# ---- Feature: Structured Output (JSON + schema) ----
def generate_trip_plan(
    client: genai.Client,
    destination: str,
    num_days: int,
    trip_month: str,
    interests: list[str],
    budget_level: str,
    weather: str,
) -> TripPlan:
    prompt = (
        f"Make a {num_days}-day trip plan for {destination} in {trip_month}.\n"
        f"Traveler interests: {', '.join(interests)}. Budget: {budget_level}.\n"
        f"Current weather note: {weather}\n"
        "Return a day-by-day trip plan as JSON that matches the schema."
    )
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.7,  # some variety, but still makes sense
        response_mime_type="application/json",
        response_schema=TripPlan,
    )
    resp = client.models.generate_content(model=MODEL, contents=prompt, config=config)
    return resp.parsed


# ---- Feature: Multimodality (image, lab meal.png pattern) ----
def analyze_photo(client: genai.Client, source: str, question: str) -> None:
    if source.startswith(("http://", "https://")):
        data = urllib.request.urlopen(source).read()
    else:
        with open(source, "rb") as f:
            data = f.read()
    mime = mimetypes.guess_type(source)[0] or "image/jpeg"
    resp = client.models.generate_content(
        model=MODEL,
        contents=[types.Part.from_bytes(data=data, mime_type=mime), question],
        config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION, temperature=0.4),
    )
    print(resp.text)


# ---- Feature: Multi-turn chat + Streaming ----
def chat_session(client: genai.Client) -> None:
    chat = client.chats.create(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.6,
        ),
    )
    print("TripSmith chat — type your travel questions. 'exit' to quit.\n")
    while True:
        try:
            user = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user or user.lower() in {"exit", "quit"}:
            break
        print("bot > ", end="", flush=True)
        for chunk in chat.send_message_stream(user):
            if chunk.text:
                print(chunk.text, end="", flush=True)
        print("\n")


# ---- Feature: thinking_level (Gemini 3 reasoning control) ----
def compare_thinking(client: genai.Client, question: str) -> None:
    for level in ("low", "high"):
        print(f"\n===== thinking_level = {level} =====")
        try:
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.6,
                thinking_config=types.ThinkingConfig(thinking_level=level),
            )
            resp = client.models.generate_content(model=MODEL, contents=question, config=config)
            print(resp.text)
        except Exception as e:  # thinking_level needs a Gemini 3 model
            print(f"[skipped: {e}]\n(Use a Gemini 3 model, e.g. GEMINI_MODEL=gemini-3.1-pro.)")


def cmd_plan(args: argparse.Namespace) -> None:
    client = get_client()
    interests = [s.strip() for s in args.interests.split(",") if s.strip()]

    print(f"Checking weather for {args.destination} (function calling)...\n")
    weather = fetch_weather(client, args.destination)
    print(weather)

    print("\nMaking your trip plan...\n")
    plan = generate_trip_plan(
        client, args.destination, args.days, args.month, interests, args.budget, weather
    )
    print(json.dumps(plan.model_dump(), indent=2, ensure_ascii=False))

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(plan.model_dump(), f, indent=2, ensure_ascii=False)
        print(f"\nSaved to {args.out}")


def cmd_weather(args: argparse.Namespace) -> None:
    print(fetch_weather(get_client(), args.destination))


def cmd_photo(args: argparse.Namespace) -> None:
    analyze_photo(get_client(), args.image, args.question)


def cmd_chat(args: argparse.Namespace) -> None:
    chat_session(get_client())


def cmd_thinking(args: argparse.Namespace) -> None:
    compare_thinking(get_client(), args.question)


def main() -> None:
    parser = argparse.ArgumentParser(description="TripSmith — AI Travel Trip Planner")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("plan", help="Full run: weather (function calling) + trip plan (JSON)")
    p.add_argument("destination")
    p.add_argument("--days", type=int, default=3)
    p.add_argument("--month", default="the upcoming season")
    p.add_argument("--interests", default="food, culture, nature")
    p.add_argument("--budget", default="mid", choices=["low", "mid", "high"])
    p.add_argument("--out", help="Write the trip plan JSON to this file")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("weather", help="Weather via function calling (lab get_weather)")
    p.add_argument("destination")
    p.set_defaults(func=cmd_weather)

    p = sub.add_parser("photo", help="Analyze a place photo (multimodality)")
    p.add_argument("image", help="Local path or image URL")
    p.add_argument("question", nargs="?", default="What place is this and is it worth visiting?")
    p.set_defaults(func=cmd_photo)

    p = sub.add_parser("chat", help="Multi-turn streaming chat")
    p.set_defaults(func=cmd_chat)

    p = sub.add_parser("thinking", help="Compare thinking_level low vs high (Gemini 3)")
    p.add_argument("question")
    p.set_defaults(func=cmd_thinking)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
