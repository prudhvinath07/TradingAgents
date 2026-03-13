"""
Vertex AI Gemini with Google Search grounding for news fetching.

Uses Gemini's built-in Google Search tool to fetch and summarize
real-time news with source citations.
"""

import json
from typing import Annotated
from datetime import datetime
from dateutil.relativedelta import relativedelta

import google.auth
import google.auth.transport.requests
import requests as http_requests

from .config import get_config


def _get_vertex_config():
    """Get Vertex AI project and location from config."""
    config = get_config()
    project_id = config.get("gcp_project_id")
    location = config.get("gcp_location", "global")

    if not project_id:
        import google.auth
        _, project_id = google.auth.default()

    return project_id, location


def _call_gemini_with_search(prompt: str, model: str = "gemini-2.5-flash") -> dict:
    """
    Call Gemini via Vertex AI REST API with Google Search grounding.

    Returns dict with 'text' and 'sources' keys.
    """
    project_id, location = _get_vertex_config()

    # Get access token via ADC
    creds, _ = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)

    # Build endpoint URL
    if location == "global":
        base_url = "https://aiplatform.googleapis.com"
    else:
        base_url = f"https://{location}-aiplatform.googleapis.com"

    url = (
        f"{base_url}/v1/projects/{project_id}/locations/{location}"
        f"/publishers/google/models/{model}:generateContent"
    )

    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ],
        "tools": [{"google_search": {}}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 4096,
        },
    }

    response = http_requests.post(
        url,
        headers={
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )

    if response.status_code != 200:
        raise Exception(f"Vertex AI API error {response.status_code}: {response.text[:500]}")

    data = response.json()

    if "candidates" not in data:
        raise Exception(f"No candidates in response: {json.dumps(data)[:500]}")

    candidate = data["candidates"][0]
    text = candidate["content"]["parts"][0].get("text", "")

    # Extract grounding sources
    sources = []
    grounding_meta = candidate.get("groundingMetadata", {})
    for chunk in grounding_meta.get("groundingChunks", []):
        web = chunk.get("web", {})
        if web:
            sources.append({
                "title": web.get("title", ""),
                "uri": web.get("uri", ""),
            })

    return {"text": text, "sources": sources}


def get_vertex_grounded_news(
    query: Annotated[str, "Query to search with (ticker symbol)"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    Fetch stock news using Gemini with Google Search grounding.

    Args:
        query: ticker symbol or company name
        start_date: Start date in yyyy-mm-dd format
        end_date: End date in yyyy-mm-dd format

    Returns:
        Formatted string with grounded news results
    """
    prompt = (
        f"Search for the latest news about {query} stock between {start_date} and {end_date}. "
        f"List each news article with:\n"
        f"- Headline\n"
        f"- Source name\n"
        f"- Brief 1-2 sentence summary\n"
        f"Focus on market-moving news, earnings, analyst ratings, and significant company events. "
        f"Return at least 5 articles if available."
    )

    try:
        result = _call_gemini_with_search(prompt)
        text = result["text"]
        sources = result["sources"]

        output = f"## {query} News (via Gemini Search), from {start_date} to {end_date}:\n\n"
        output += text

        if sources:
            output += "\n\n### Sources:\n"
            for s in sources[:8]:
                output += f"- {s['title']}\n"

        return output

    except Exception as e:
        print(f"Vertex grounding news failed: {e}")
        return f"[DATA UNAVAILABLE] Vertex AI grounded search failed for {query}: {e}"


def get_vertex_grounded_global_news(
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "Number of days to look back"] = 7,
    limit: Annotated[int, "Maximum number of articles to return"] = 10,
) -> str:
    """
    Fetch global financial news using Gemini with Google Search grounding.

    Args:
        curr_date: Current date in yyyy-mm-dd format
        look_back_days: Number of days to look back (default 7)
        limit: Maximum number of articles to return (default 10)

    Returns:
        Formatted string with global news
    """
    start_date_dt = datetime.strptime(curr_date, "%Y-%m-%d") - relativedelta(days=look_back_days)
    start_date = start_date_dt.strftime("%Y-%m-%d")

    prompt = (
        f"Search for the top {limit} global financial and market news stories "
        f"between {start_date} and {curr_date}. Cover:\n"
        f"- Major stock market moves (S&P 500, Nasdaq, global indices)\n"
        f"- Federal Reserve / central bank decisions\n"
        f"- Inflation and economic data\n"
        f"- Commodities (oil, gold)\n"
        f"- Major corporate news\n\n"
        f"For each article, provide the headline, source, and a brief summary."
    )

    try:
        result = _call_gemini_with_search(prompt)
        text = result["text"]
        sources = result["sources"]

        output = (
            f"## Global Market & Financial News (via Gemini Search)\n"
            f"**Period:** {start_date} to {curr_date}\n\n"
        )
        output += text

        if sources:
            output += "\n\n### Sources:\n"
            for s in sources[:8]:
                output += f"- {s['title']}\n"

        return output

    except Exception as e:
        print(f"Vertex grounding global news failed: {e}")
        return f"[DATA UNAVAILABLE] Vertex AI grounded search failed for global news: {e}"
