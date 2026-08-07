"""TripSmith — AI Travel Itinerary Planner.

Built on Google Gen AI SDK (google-genai), extending Lab GSP1150 (Gemini 3).
Features used: System Instructions, Structured Output (JSON schema),
Grounding (Google Search), Multi-turn chat + streaming, thinking_level compare.
"""

import argparse
import json
import os
from enum import Enum

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv()

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

SYSTEM_INSTRUCTION = (
    "You are TripSmith, a seasoned local travel guide with 15 years of experience.\n"
    "- Give practical, realistic itineraries — account for travel time between spots.\n"
    "- Respect the traveler's budget level and interests; never suggest closed/seasonal spots.\n"
    "- Prefer authentic local experiences over tourist traps.\n"
    "- Be concise. When asked for JSON, output ONLY valid JSON matching the schema."
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


class Itinerary(BaseModel):
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


# ---- Feature: Grounding (Google Search) ----
def fetch_insights(client: genai.Client, destination: str, trip_month: str) -> tuple[str, list[str]]:
    prompt = (
        f"Search for current, {trip_month}-specific travel information about {destination}: "
        "seasonal festivals/events, weather to expect, and 3 timely local tips. "
        "Return a tight bullet summary with concrete names and dates."
    )
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.2,  # factual accuracy over creativity
        tools=[types.Tool(google_search=types.GoogleSearch())],
    )
    resp = client.models.generate_content(model=MODEL, contents=prompt, config=config)

    citations: list[str] = []
    meta = resp.candidates[0].grounding_metadata if resp.candidates else None
    if meta and meta.grounding_chunks:
        for chunk in meta.grounding_chunks:
            if chunk.web and chunk.web.uri:
                citations.append(f"{chunk.web.title or 'source'} — {chunk.web.uri}")
    return resp.text or "", citations


# ---- Feature: Structured Output (JSON + schema) ----
def generate_itinerary(
    client: genai.Client,
    destination: str,
    num_days: int,
    trip_month: str,
    interests: list[str],
    budget_level: str,
    insights: str,
) -> Itinerary:
    prompt = (
        f"Plan a {num_days}-day trip to {destination} in {trip_month}.\n"
        f"Traveler interests: {', '.join(interests)}. Budget: {budget_level}.\n"
        f"Use these fresh insights when relevant:\n<<< {insights} >>>\n"
        "Produce a day-by-day itinerary as JSON per the provided schema."
    )
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.7,  # creative but coherent suggestions
        response_mime_type="application/json",
        response_schema=Itinerary,
    )
    resp = client.models.generate_content(model=MODEL, contents=prompt, config=config)
    return resp.parsed


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


# ---- Bonus: thinking_level comparison (Gemini 3) ----
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
        except Exception as e:  # thinking_level requires a Gemini 3 model
            print(f"[skipped: {e}]\n(Set GEMINI_MODEL=gemini-3-pro-preview to use thinking_level.)")


def cmd_plan(args: argparse.Namespace) -> None:
    client = get_client()
    interests = [s.strip() for s in args.interests.split(",") if s.strip()]

    print(f"Fetching current insights for {args.destination} ({args.month})...\n")
    insights, citations = fetch_insights(client, args.destination, args.month)
    print(insights)
    if citations:
        print("\nSources:")
        for c in citations:
            print(f"  - {c}")

    print("\nGenerating itinerary...\n")
    itinerary = generate_itinerary(
        client, args.destination, args.days, args.month, interests, args.budget, insights
    )
    print(json.dumps(itinerary.model_dump(), indent=2, ensure_ascii=False))

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(itinerary.model_dump(), f, indent=2, ensure_ascii=False)
        print(f"\nSaved to {args.out}")


def cmd_insights(args: argparse.Namespace) -> None:
    client = get_client()
    insights, citations = fetch_insights(client, args.destination, args.month)
    print(insights)
    if citations:
        print("\nSources:")
        for c in citations:
            print(f"  - {c}")


def cmd_chat(args: argparse.Namespace) -> None:
    chat_session(get_client())


def cmd_thinking(args: argparse.Namespace) -> None:
    compare_thinking(get_client(), args.question)


def main() -> None:
    parser = argparse.ArgumentParser(description="TripSmith — AI Travel Itinerary Planner")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("plan", help="Full pipeline: grounded insights + structured itinerary")
    p.add_argument("destination")
    p.add_argument("--days", type=int, default=3)
    p.add_argument("--month", default="the upcoming season")
    p.add_argument("--interests", default="food, culture, nature")
    p.add_argument("--budget", default="mid", choices=["low", "mid", "high"])
    p.add_argument("--out", help="Write itinerary JSON to this file")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("insights", help="Grounded Google Search insights only")
    p.add_argument("destination")
    p.add_argument("--month", default="the upcoming season")
    p.set_defaults(func=cmd_insights)

    p = sub.add_parser("chat", help="Multi-turn streaming chat")
    p.set_defaults(func=cmd_chat)

    p = sub.add_parser("thinking", help="Compare thinking_level low vs high (Gemini 3)")
    p.add_argument("question")
    p.set_defaults(func=cmd_thinking)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
