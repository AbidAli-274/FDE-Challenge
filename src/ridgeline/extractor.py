"""One shared LLM extractor: reader text in, validated ExtractedRFQ out."""
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError

from .schema import ExtractedLine, ExtractedRFQ

PROMPT = (Path(__file__).parent / "extraction_prompt.txt").read_text(encoding="utf-8")
TOOL = {
    "type": "function",
    "function": {
        "name": "submit_rfq",
        "description": "Submit the extracted RFQ line items.",
        "parameters": ExtractedRFQ.model_json_schema(),
    },
}


def _unparseable(raw=None) -> ExtractedLine:
    text = raw if isinstance(raw, str) and raw.strip() else "unparseable line"
    return ExtractedLine(as_written=text, flags=["unparseable"])


def validate(args) -> ExtractedRFQ:
    """Validate per line so one bad line does not lose the rest."""
    if not isinstance(args, dict) or not isinstance(args.get("lines"), list):
        return ExtractedRFQ(lines=[_unparseable("entire RFQ")])
    lines = []
    for raw in args["lines"]:
        try:
            lines.append(ExtractedLine.model_validate(raw))
        except ValidationError:
            lines.append(_unparseable(raw.get("as_written") if isinstance(raw, dict) else raw))
    company = args.get("company")
    return ExtractedRFQ(company=company if isinstance(company, str) else None, lines=lines)


def extract(text: str) -> ExtractedRFQ:
    load_dotenv()
    # Groq exposes an OpenAI-compatible API, so the openai client is reused.
    client = OpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url=os.getenv("GROQ_BASE_URL") or "https://api.groq.com/openai/v1",
    )
    resp = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL") or "openai/gpt-oss-120b",
        temperature=0,
        messages=[{"role": "system", "content": PROMPT}, {"role": "user", "content": text}],
        tools=[TOOL],
        tool_choice={"type": "function", "function": {"name": "submit_rfq"}},
    )
    calls = resp.choices[0].message.tool_calls
    try:
        args = json.loads(calls[0].function.arguments)
    except (TypeError, IndexError, json.JSONDecodeError):
        args = None
    return validate(args)
